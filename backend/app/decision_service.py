"""供 API、传感器和人工审核调用的可复用决策流水线。"""

import asyncio
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List
from uuid import uuid4

from . import state
from .agents.decision_agent import decision_agent
from .agents.hitl_agent import hitl_agent
from .agents.orchestrator import run_all
from .crop_identification_agent import identify_crop
from .crop_profile import analyze_crop_conditions_async
from .device_health import check_health, reset_actuator_circuit
from .services import audit, safety
from .tools.actuator_tool import dispatch_commands

# 智能体英文名 → 中文名映射：用于置信度不足时向农户生成可读的中文提示。
AGENT_NAMES_ZH = {
    "soil": "土壤智能体",
    "temperature": "温度智能体",
    "humidity": "湿度智能体",
    "pest": "病虫害智能体",
    "irrigation": "灌溉智能体",
    "light_co2": "光照与 CO₂ 智能体",
    "crop_stage": "生育期智能体",
    "crop_identification": "作物识别智能体",
}


# 自定义异常：审批项已处理过（状态非 pending）时再次处理抛出，防止重复审批。
class HitlAlreadyResolvedError(RuntimeError):
    pass


def _open_hitl_once(kind: str, signature: str, payload: Dict[str, Any]) -> bool:
    """同一事件保持活跃期间只创建一次审批。"""
    if any(
        item.get("incident_active")
        and item.get("incident_kind") == kind
        and item.get("incident_signature") == signature
        for item in state.hitl
    ):
        return False
    item = {
        "id": str(uuid4()),
        **payload,
        "status": "pending",
        "incident_kind": kind,
        "incident_signature": signature,
        "incident_active": True,
    }
    state.hitl.insert(0, item)
    audit("hitl_pending", item)
    return True


# 把指定 kind 的审批事件标记为已结束：事件消除后不再拦截后续决策。
def _clear_hitl_incident(kind: str) -> None:
    for item in state.hitl:
        if item.get("incident_kind") == kind:
            item["incident_active"] = False


# 单个智能体运行结果的统一结构：归一化各智能体返回字段，未知字段收进 extra。
@dataclass
class AgentResult:
    agent: str
    status: str = "ok"
    confidence: float = 1.0
    findings: List[Any] = field(default_factory=list)
    recommendations: List[Any] = field(default_factory=list)
    risk_level: str = "low"
    extra: Dict[str, Any] = field(default_factory=dict)

    # 从智能体返回的字典构造实例：缺省值容错，未识别的附加字段保留在 extra。
    @classmethod
    def from_value(cls, value: Dict[str, Any]) -> "AgentResult":
        data = dict(value or {})
        return cls(
            agent=str(data.pop("agent", "unknown")),
            status=str(data.pop("status", "ok")),
            confidence=float(data.pop("confidence", 1.0) or 0.0),
            findings=list(data.pop("findings", []) or []),
            recommendations=list(data.pop("recommendations", []) or []),
            risk_level=str(data.pop("risk_level", "low")),
            extra=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "agent": self.agent,
            "status": self.status,
            "confidence": self.confidence,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "risk_level": self.risk_level,
        }
        result.update(self.extra)
        return result


# 执行器分发结果：status 为分发状态，count 为成功下发的命令数。
@dataclass
class DispatchResult:
    status: str
    count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Dict[str, Any]) -> "DispatchResult":
        data = dict(value or {})
        return cls(
            str(data.pop("status", "dispatch_failed")),
            int(data.pop("count", 0) or 0),
            data,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {"status": self.status, "count": self.count}
        result.update(self.extra)
        return result


# 一次完整决策运行的产物：动作清单、人工介入标记、给农户的解释、审计与分发信息。
@dataclass
class DecisionResult:
    id: str
    priority_actions: List[Dict[str, Any]]
    human_intervention: bool
    explanation_for_farmer: str
    audit: Dict[str, Any]
    dispatch: DispatchResult
    action_alerts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "priority_actions": self.priority_actions,
            "human_intervention": self.human_intervention,
            "explanation_for_farmer": self.explanation_for_farmer,
            "audit": self.audit,
            "dispatch": self.dispatch.to_dict(),
            "action_alerts": self.action_alerts,
        }


class DecisionService:
    """执行一次完整的识别、融合、安全检查和分发流程。"""

    # 一次完整决策运行：识别作物→各智能体分析→动作融合→安全/审批检查→分发或挂起审批。
    async def run(
        self,
        reading: Any = None,
        trigger: str = "api",
        approved_signature: str = "",
    ) -> DecisionResult:
        reading = reading or state.latest
        # 作物档案缺少作物名，或档案置信度低于 0.7 时，认为需要重新识别作物。
        profile_confidence = float(state.crop_profile.get("confidence") or 1.0)
        needs_identification = (
            not state.crop_profile.get("crop") or profile_confidence < 0.7
        )
        # 需要识别且本次读数带图像时，在后台线程执行作物识别，避免阻塞事件循环。
        if needs_identification and getattr(reading, "image_url", None):
            identification = await asyncio.to_thread(
                identify_crop, reading.image_url, {"device_id": reading.device_id}
            )
            state.last_crop_identification = identification
            # 识别无需人工确认：关闭旧的识别审批事件，并立即重建作物条件档案。
            if not identification["human_intervention"]["required"]:
                _clear_hitl_incident("crop_identification")
                sensor_data = (
                    reading.model_dump()
                    if hasattr(reading, "model_dump")
                    else reading.dict()
                )
                state.crop_profile = await analyze_crop_conditions_async(
                    identification["crop"], context={"sensor_data": sensor_data}
                )
                audit("crop_profile_analysis", state.crop_profile)
            else:
                # 识别置信度不足：为同一识别事件创建一次审批，请求人工确认作物种类。
                reason = identification["human_intervention"]["reason"]
                question = identification["human_intervention"]["question_to_human"]
                _open_hitl_once(
                    "crop_identification",
                    json.dumps([reason, question], ensure_ascii=False),
                    {
                        "type": "crop_identification",
                        "reason": reason,
                        "question": question,
                    },
                )
            audit("crop_identification", identification)

        # 编排运行全部智能体：读取传感器数据与作物档案，产出各智能体的分析与建议。
        raw_agents = list(await run_all(reading, state.crop_profile))
        agents = [AgentResult.from_value(agent) for agent in raw_agents]
        state.agent_cache = [agent.to_dict() for agent in agents]
        # 由决策智能体融合各智能体建议，生成动作命令；safety_rules 给出温度与 pH 的硬边界。
        commands = decision_agent.fuse(
            state.agent_cache,
            {
                "crop_profile": state.crop_profile,
                "actuator_state": state.actuator_state,
                "safety_rules": {
                    "temperature_max": 40,
                    "temperature_min": 5,
                    "ph_min": 4,
                    "ph_max": 8,
                },
            },
        )
        # 从 HITL 智能体、安全规则门、传感器健康检查三方收集需要人工介入的原因。
        check = hitl_agent.evaluate(reading, commands)
        reasons = list(check["reasons"])
        gate, safety_reasons = safety(reading, commands)
        reasons.extend(safety_reasons)
        sensor_health_reasons = [
            issue["message"] for issue in check_health()["sensor"]["issues"]
        ]
        reasons.extend(sensor_health_reasons)
        action_alerts = list(getattr(decision_agent, "last_alerts", []))
        action_hitl = list(getattr(decision_agent, "last_hitl_actions", []))
        reasons.extend(
            alert["message"] for alert in action_alerts if alert.get("requires_hitl")
        )
        # 除作物识别与生育期智能体外，置信度低于 0.7 的智能体视为置信度不足，需要人工审批。
        low_confidence = [
            agent.agent
            for agent in agents
            if agent.agent not in ("crop_identification", "crop_stage")
            and agent.confidence < 0.7
        ]
        if low_confidence:
            names = "、".join(AGENT_NAMES_ZH.get(name, name) for name in low_confidence)
            reasons.append("智能体置信度不足：" + names)
        crop_pending = bool(
            (state.last_crop_identification or {})
            .get("human_intervention", {})
            .get("required")
        )
        if crop_pending:
            reasons.append("作物识别结果需要人工确认")
        # 安全阻断条件：HITL 不放行、安全门不放行、任一智能体低置信度、存在待人工动作或传感器故障。
        safety_block = (
            check["status"] != "allow"
            or gate != "allow"
            or bool(low_confidence)
            or bool(action_hitl)
            or bool(sensor_health_reasons)
        )
        # 审批签名 = 命令集合 + 原因集合：内容相同即视为同一事件，避免重复审批。
        signature = json.dumps(
            {
                "commands": sorted(
                    (str(command.get("actuator")), str(command.get("action")))
                    for command in commands
                ),
                "reasons": sorted(set(reasons)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        # 本次签名与已批准签名一致，说明同一事件已被人工批准过，可直接放行。
        approval_matches = safety_block and signature == approved_signature
        needs_approval = safety_block and not approval_matches
        # 组装决策结果：需要审批则仅挂起（blocked_by_safety），否则稍后直接下发。
        decision = DecisionResult(
            id=str(uuid4()),
            priority_actions=commands,
            human_intervention=needs_approval or crop_pending,
            explanation_for_farmer="；".join(dict.fromkeys(reasons))
            or "环境指标正常，无需人工审批",
            audit={"agents": state.agent_cache},
            dispatch=(
                DispatchResult("blocked_by_safety", len(commands))
                if needs_approval
                else DispatchResult("pending")
            ),
            action_alerts=action_alerts,
        )
        # 需要审批：为决策创建审批单挂起；否则直接分发命令并关闭旧的决策审批事件。
        if needs_approval:
            _open_hitl_once(
                "decision",
                signature,
                {
                    "type": "decision",
                    "decision_id": decision.id,
                    "reason": decision.explanation_for_farmer,
                },
            )
        else:
            _clear_hitl_incident("decision")
            decision.dispatch = DispatchResult.from_value(dispatch_commands(commands))
        payload = decision.to_dict()
        state.decisions.insert(0, payload)
        audit("decision", payload)
        return decision

    # 按 id 将审批项置为目标状态；若已处理过则抛出 HitlAlreadyResolvedError。
    def resolve_hitl(self, item_id: str, status: str) -> Dict[str, Any]:
        for item in state.hitl:
            if item.get("id") == item_id:
                if item.get("status") != "pending":
                    raise HitlAlreadyResolvedError(item_id)
                item["status"] = status
                audit("hitl_" + status, item)
                return item
        raise KeyError(item_id)

    # 人工审批通过入口：设备故障直接复位熔断；决策类审批携带签名重跑决策链后再执行。
    async def approve_hitl(self, item_id: str) -> Dict[str, Any]:
        item = next(
            (request for request in state.hitl if request.get("id") == item_id), None
        )
        if item is None:
            raise KeyError(item_id)
        if item.get("status") != "pending":
            raise HitlAlreadyResolvedError(item_id)
        signature = item.get("incident_signature")
        # 设备故障审批通过后，复位对应执行器的熔断电路，让设备恢复可用。
        if item.get("type") == "device_failure":
            item = self.resolve_hitl(item_id, "approved")
            reset_actuator_circuit(str(item.get("actuator", "")))
            return item
        # 非决策类审批（如作物识别）：直接标记通过即可，无需重跑决策。
        if item.get("type") != "decision" or not signature:
            return self.resolve_hitl(item_id, "approved")

        # 重新运行完整决策链，禁止直接执行审批期间可能已经过期的旧命令。
        decision = await self.run(
            state.latest,
            trigger="hitl_approval",
            approved_signature=signature,
        )
        item = self.resolve_hitl(item_id, "approved")
        item["incident_active"] = False
        result = {**item, "revalidation": decision.to_dict()}
        audit(
            "hitl_revalidated",
            {
                "hitl_id": item_id,
                "decision_id": decision.id,
                "dispatch": decision.dispatch.to_dict(),
                "human_intervention": decision.human_intervention,
            },
        )
        return result


# 模块级单例：API 层与人工审批都复用同一个决策服务实例。
decision_service = DecisionService()


# 便捷入口函数：使用单例运行一次决策。
async def run_decision(reading: Any = None, trigger: str = "api") -> DecisionResult:
    return await decision_service.run(reading, trigger)


__all__ = [
    "AgentResult",
    "DispatchResult",
    "DecisionResult",
    "DecisionService",
    "decision_service",
    "run_decision",
]
