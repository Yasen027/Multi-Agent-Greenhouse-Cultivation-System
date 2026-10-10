# 多智能体与作物识别 API：手动触发评估、查询状态、作物识别及人工确认流程。
from uuid import uuid4

from fastapi import APIRouter

from .. import state
from ..crop_identification_agent import identify_crop
from ..crop_profile import analyze_crop_conditions
from ..crop_trigger import manager
from ..decision_service import decision_service
from ..schemas import CropTriggerRequest
from ..services import audit

router = APIRouter(prefix="/api/agents", tags=["agents"])
# 与 registry.AGENT_NAMES 保持一致，用于状态兜底展示。
NAMES = [
    "soil",
    "temperature",
    "humidity",
    "pest",
    "irrigation",
    "light_co2",
    "crop_stage",
    "crop_identification",
]


@router.post("/run")
async def run():
    # 手动触发一轮完整的决策评估（trigger 标记为 api 来源）。
    result = await decision_service.run(trigger="api")
    return result.to_dict()


@router.get("/status")
def status():
    # 有缓存则返回各 Agent 最近结果；无缓存时用默认空闲状态兜底。
    return state.agent_cache or [
        {"agent": n, "status": "idle", "confidence": 0.0} for n in NAMES
    ]


@router.post("/crop-identification")
def identify(payload: dict):
    # 从请求体读取 image_url/metadata/user_input 直接发起一次作物识别。
    result = identify_crop(
        payload.get("image_url"), payload.get("metadata"), payload.get("user_input", "")
    )
    state.last_crop_identification = result
    # 识别需要人工介入时，写入 HITL 待办列表。
    if result["human_intervention"]["required"]:
        state.hitl.insert(
            0,
            {
                "id": str(uuid4()),
                "type": "crop_identification",
                "reason": result["human_intervention"]["reason"],
                "question": result["human_intervention"]["question_to_human"],
                "status": "pending",
            },
        )
    audit("crop_identification", result)
    return result


@router.post("/crop-identification/run")
def run_crop(req: CropTriggerRequest):
    # 触发周期可调，但强制下限 1 小时，防止过于频繁的识别请求。
    if req.interval_hours is not None:
        manager.interval_hours = max(1, req.interval_hours)
    # 非强制且未到周期（profile_mismatch 除外）时直接返回 not_due。
    if not manager.should_run(req.reason, req.force, req.reason == "profile_mismatch"):
        return {
            "triggered": False,
            "reason": "not_due",
            "status": manager.status(),
            "profile": state.crop_profile,
        }
    # 无图片时回退到最新读数的图片；元数据回退到当前设备 ID。
    result = identify_crop(
        req.image_url or state.latest.image_url,
        req.metadata or {"device_id": state.latest.device_id},
        req.user_input or "",
    )
    state.last_crop_identification = result
    # 需人工介入或识别结果为 unknown：先挂起 HITL，等待人工确认。
    if result["human_intervention"]["required"] or result["crop"] == "unknown":
        hitl_item = {
            "id": str(uuid4()),
            "reason": result["human_intervention"]["reason"],
            "question": result["human_intervention"]["question_to_human"],
            "status": "pending",
            "type": "crop_identification",
        }
        state.hitl.insert(0, hitl_item)
        audit("crop_identification_pending", {"trigger": req.reason, "result": result})
        return {
            "triggered": True,
            "reason": "human_confirmation_required",
            "status": manager.status(),
            "profile": state.crop_profile,
            "identification": result,
            "hitl": hitl_item,
        }
    # 兼容 Pydantic v1/v2 序列化最新读数，作为条件分析上下文。
    sensor_data = (
        state.latest.model_dump()
        if hasattr(state.latest, "model_dump")
        else state.latest.dict()
    )
    # 基于识别结果与当前传感器数据生成作物环境档案，并写入全局状态。
    profile = analyze_crop_conditions(
        result["crop"], context={"sensor_data": sensor_data}
    )
    profile["confidence"] = result["confidence"]
    profile["identification_method"] = result["method"]
    state.crop_profile = profile
    manager.current_crop = result["crop"]
    # 标记本次触发已完成，更新下次触发周期。
    manager.mark(req.reason)
    audit(
        "crop_identification",
        {"trigger": req.reason, "result": result, "profile": profile},
    )
    return {
        "triggered": True,
        "reason": req.reason,
        "status": manager.status(),
        "profile": profile,
        "identification": result,
    }


@router.post("/crop-identification/analyze")
def analyze_crop(payload: dict):
    # 作物名缺省时回退到当前档案；stage 也可由请求体指定。
    crop = payload.get("crop") or (state.crop_profile or {}).get("crop")
    profile = analyze_crop_conditions(
        crop or "unknown", payload.get("stage", "unknown"), payload
    )
    # 只有识别出具体作物时才更新全局档案，unknown 不覆盖。
    if profile.get("crop") != "unknown":
        state.crop_profile = profile
    audit("crop_profile_analysis", profile)
    return profile


@router.post("/crop-identification/confirm")
def confirm_crop(payload: dict):
    crop = str(payload.get("crop", "unknown")).lower().strip()
    # 白名单校验：仅支持这五种作物，其他一律拒绝。
    if crop not in ("tomato", "lettuce", "strawberry", "cucumber", "pepper"):
        return {"status": "rejected", "reason": "unsupported crop"}
    profile = analyze_crop_conditions(crop, payload.get("stage", "unknown"), payload)
    state.crop_profile = profile
    state.last_crop_identification = {
        "crop": crop,
        # 人工确认视为完全可信。
        "confidence": 1.0,
        "method": "human_confirmation",
        "human_intervention": {"required": False},
    }
    # 把所有 pending 状态的作物识别 HITL 单标记为已解决。
    for item in state.hitl:
        if (
            item.get("type") == "crop_identification"
            and item.get("status") == "pending"
        ):
            item["status"] = "resolved"
            item["incident_active"] = False
    manager.current_crop = crop
    manager.mark("human_confirmation")
    audit("crop_identification_confirmed", profile)
    return {"status": "confirmed", "profile": profile}


@router.get("/crop-identification/status")
def crop_status():
    # 一次性返回当前档案、最近识别结果与触发周期状态。
    return {
        "profile": state.crop_profile,
        "identification": state.last_crop_identification,
        "trigger": manager.status(),
    }
