# 生育阶段 Agent：从作物档案读取当前阶段，生成阈值更新建议。
from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class CropStageAgent(BaseAgent):
    # 关注作物当前生育阶段，建议系统按阶段刷新各项环境阈值。
    name = "crop_stage"
    prompt_name = "crop_stage"

    async def run(self, context: dict[str, Any]):
        profile = context.get("crop_profile") or {}
        # 档案缺失或非字典时按 unknown 处理。
        stage = (
            profile.get("stage", "unknown") if isinstance(profile, dict) else "unknown"
        )
        # 已知阶段置信度 0.8；阶段未知时降为 0.5。
        confidence = 0.8 if stage != "unknown" else 0.5
        prompt = prompt_loader.load(
            "crop_stage",
            {
                "crop": (
                    profile.get("crop", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "sensor_data_json": context["reading"].model_dump(),
                "history_json": context.get("history", {}),
                "crop_profile_json": profile,
                "context": context.get("extra", {}),
                "weather_json": context.get("weather", {}),
            },
        )
        return self.result(
            confidence=confidence,
            findings=[f"stage={stage}"],
            # 建议下游按当前阶段更新环境阈值（该动作由提示词/融合层解释）。
            recommendations=["update_stage_thresholds"],
            # 置信度不足 0.7 视为中等风险，提示阶段信息不完整。
            risk_level="medium" if confidence < 0.7 else "low",
            prompt_loaded=bool(prompt),
            stage=stage,
        )
