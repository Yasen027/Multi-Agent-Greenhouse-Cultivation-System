# 作物识别智能体：基于图像/文件名/元数据识别作物种类，识别不足时请求人工确认。
import asyncio
import logging
from typing import Any, Dict, Optional

from .crop_profile import analyze_crop_conditions_async
from .deepseek_client import DeepSeekError, deepseek_client
from .prompt_loader import prompt_loader

logger = logging.getLogger(__name__)

# 系统支持的作物及其常见别名：用于命中判断和关键词回退识别。
CROP_HINTS = {
    "tomato": ("tomato", "番茄", "西红柿"),
    "lettuce": ("lettuce", "生菜"),
    "strawberry": ("strawberry", "草莓"),
    "cucumber": ("cucumber", "黄瓜"),
    "pepper": ("pepper", "辣椒"),
}


# 组装作物识别的提示词上下文。
def build_prompt(context: Dict[str, Any]) -> str:
    return prompt_loader.load("crop_identification", context)


# 构造人工介入结构：不需要时清空 urgency 与问题文案，保证输出干净。
def _hitl(required: bool, reason: str = "", urgency: str = "none") -> Dict[str, Any]:
    return {
        "required": required,
        "urgency": urgency if required else "none",
        "reason": reason,
        "question_to_human": "请确认当前温室种植的作物和品种。" if required else "",
    }


# 归一化模型返回：统一作物名、裁剪置信度，低于 0.7 或未知作物即要求人工确认。
def _normalize(result: Dict[str, Any], method: str) -> Dict[str, Any]:
    crop = (
        str(result.get("crop") or result.get("crop_species") or "unknown")
        .lower()
        .strip()
    )
    aliases = {
        "西红柿": "tomato",
        "番茄": "tomato",
        "tomatoes": "tomato",
        "生菜": "lettuce",
        "lettuces": "lettuce",
        "草莓": "strawberry",
        "strawberries": "strawberry",
        "黄瓜": "cucumber",
        "cucumbers": "cucumber",
        "辣椒": "pepper",
        "peppers": "pepper",
    }
    crop = aliases.get(crop, crop)
    # 置信度裁剪到 [0,1]，非数值一律按 0 处理。
    try:
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    required = confidence < 0.7 or crop not in CROP_HINTS
    human = (
        result.get("human_intervention")
        if isinstance(result.get("human_intervention"), dict)
        else {}
    )
    reason = str(human.get("reason", ""))
    # 模型未给出中文原因时补一个通用中文提示，保证前端可展示。
    if required and not any("\u4e00" <= char <= "\u9fff" for char in reason):
        reason = "作物识别置信度不足或作物未知"
    human = _hitl(
        required,
        reason or ("作物识别置信度不足或作物未知" if required else ""),
        human.get("urgency", "medium"),
    )
    return {
        "crop": crop,
        "crop_species": result.get("crop_species") or crop,
        "crop_variety": result.get("crop_variety"),
        "crop_profile_key": crop if crop in CROP_HINTS else None,
        "confidence": confidence,
        "method": method,
        "evidence": result.get("evidence") or [],
        "human_intervention": human,
    }


# 识别主入口：优先视觉模型；失败后按文件名/元数据关键词回退，最后返回低置信度 unknown。
def identify_crop(
    image_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_input: str = "",
) -> Dict[str, Any]:
    metadata = metadata or {}
    prompt = build_prompt(
        {
            "image_data": image_url or "none",
            "user_input": user_input,
            "history_json": metadata.get("history", {}),
            "sensor_data_json": metadata.get("sensor_data", {}),
            "crop_knowledge_json": metadata.get("crop_knowledge", {}),
            "context": metadata,
        }
    )
    try:
        response = deepseek_client.complete_json(prompt, image_url=image_url)
        return _normalize(response, "deepseek_vision" if image_url else "deepseek")
    except DeepSeekError as exc:
        logger.info("Using crop identification fallback: %s", exc)
    # 回退链：模型调用失败时，用图片地址、元数据与用户输入中的作物关键词匹配。
    text = " ".join([str(image_url or ""), str(metadata), user_input]).lower()
    for crop, hints in CROP_HINTS.items():
        if any(h in text for h in hints):
            return _normalize(
                {"crop": crop, "confidence": 0.92, "evidence": text},
                "filename_or_metadata",
            )
    return _normalize(
        {"crop": "unknown", "confidence": 0.2, "evidence": text}, "fallback"
    )


# 智能体接口：识别成功且无需人工时顺带生成作物条件档案，否则建议人工确认。
async def evaluate(reading) -> dict[str, Any]:
    result = await asyncio.to_thread(
        identify_crop,
        getattr(reading, "image_url", None),
        {"device_id": getattr(reading, "device_id", "")},
    )
    profile = None
    # 只有识别出已知作物且无需人工确认时才生成作物条件档案。
    if result["crop"] in CROP_HINTS and not result["human_intervention"]["required"]:
        profile = await analyze_crop_conditions_async(result["crop"])
    return {
        "agent": "crop_identification",
        "status": "ok",
        "confidence": result["confidence"],
        "findings": result,
        "recommendations": (
            ["set_crop_profile"] if profile else ["request_human_confirmation"]
        ),
        "recommended_actions": ["设置当前作物档案"],
        "risk_level": "low" if result["confidence"] >= 0.7 else "medium",
        "crop": result["crop"],
        "method": result["method"],
        "human_intervention": result["human_intervention"],
        "crop_profile": profile,
    }
