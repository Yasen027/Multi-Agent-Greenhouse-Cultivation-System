"""Reusable decision pipeline for API, sensor and HITL callers."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4

from . import state
from .agents.decision_agent import decision_agent
from .agents.hitl_agent import hitl_agent
from .agents.orchestrator import run_all
from .crop_identification_agent import identify_crop
from .crop_profile import analyze_crop_conditions_async
from .services import audit, safety
from .tools.actuator_tool import dispatch_commands


@dataclass
class AgentResult:
    agent: str
    status: str = "ok"
    confidence: float = 1.0
    findings: List[Any] = field(default_factory=list)
    recommendations: List[Any] = field(default_factory=list)
    risk_level: str = "low"
    extra: Dict[str, Any] = field(default_factory=dict)

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


@dataclass
class DispatchResult:
    status: str
    count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Dict[str, Any]) -> "DispatchResult":
        data = dict(value or {})
        return cls(str(data.pop("status", "dispatch_failed")), int(data.pop("count", 0) or 0), data)

    def to_dict(self) -> Dict[str, Any]:
        result = {"status": self.status, "count": self.count}
        result.update(self.extra)
        return result


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
    """Runs one complete recognition -> fusion -> safety -> dispatch cycle."""

    async def run(self, reading: Any = None, trigger: str = "api") -> DecisionResult:
        reading = reading or state.latest
        profile_confidence = float(state.crop_profile.get("confidence") or 1.0)
        if (not state.crop_profile.get("crop") or profile_confidence < 0.7) and getattr(reading, "image_url", None):
            identification = await asyncio.to_thread(
                identify_crop, reading.image_url, {"device_id": reading.device_id}
            )
            state.last_crop_identification = identification
            if not identification["human_intervention"]["required"]:
                sensor_data = reading.model_dump() if hasattr(reading, "model_dump") else reading.dict()
                state.crop_profile = await analyze_crop_conditions_async(
                    identification["crop"], context={"sensor_data": sensor_data}
                )
                audit("crop_profile_analysis", state.crop_profile)
            else:
                state.hitl.insert(
                    0,
                    {
                        "id": str(uuid4()),
                        "type": "crop_identification",
                        "reason": identification["human_intervention"]["reason"],
                        "question": identification["human_intervention"]["question_to_human"],
                        "status": "pending",
                    },
                )
            audit("crop_identification", identification)

        raw_agents = list(await run_all(reading, state.crop_profile))
        agents = [AgentResult.from_value(agent) for agent in raw_agents]
        state.agent_cache = [agent.to_dict() for agent in agents]
        commands = decision_agent.fuse(
            state.agent_cache,
            {
                "crop_profile": state.crop_profile,
                "actuator_state": state.actuator_state,
                "safety_rules": {"temperature_max": 40, "temperature_min": 5, "ph_min": 4, "ph_max": 8},
            },
        )
        check = hitl_agent.evaluate(reading, commands)
        reasons = list(check["reasons"])
        gate, safety_reasons = safety(reading, commands)
        reasons.extend(safety_reasons)
        action_alerts = list(getattr(decision_agent, "last_alerts", []))
        action_hitl = list(getattr(decision_agent, "last_hitl_actions", []))
        reasons.extend(alert["message"] for alert in action_alerts if alert.get("requires_hitl"))
        low_confidence = [
            agent.agent
            for agent in agents
            if agent.agent not in ("crop_identification", "crop_stage") and agent.confidence < 0.7
        ]
        if low_confidence:
            reasons.append("low confidence agents: " + ",".join(low_confidence))
        crop_pending = bool((state.last_crop_identification or {}).get("human_intervention", {}).get("required"))
        if crop_pending:
            reasons.append("crop identification requires human confirmation")
        safety_block = check["status"] != "allow" or gate != "allow" or bool(low_confidence) or bool(action_hitl)
        decision = DecisionResult(
            id=str(uuid4()),
            priority_actions=commands,
            human_intervention=safety_block or crop_pending,
            explanation_for_farmer="; ".join(dict.fromkeys(reasons)) or "Routine environmental optimization",
            audit={"agents": state.agent_cache},
            dispatch=DispatchResult("blocked_by_safety", len(commands)) if safety_block else DispatchResult("pending"),
            action_alerts=action_alerts,
        )
        if safety_block:
            state.hitl.insert(
                0,
                {
                    "id": str(uuid4()),
                    "decision_id": decision.id,
                    "reason": decision.explanation_for_farmer,
                    "status": "pending",
                },
            )
        else:
            decision.dispatch = DispatchResult.from_value(dispatch_commands(commands))
            if decision.dispatch.status == "published":
                for command in commands:
                    state.actuator_state[command["actuator"]] = command.get("action")
        payload = decision.to_dict()
        state.decisions.insert(0, payload)
        audit("decision", payload)
        return decision

    def resolve_hitl(self, item_id: str, status: str) -> Dict[str, Any]:
        for item in state.hitl:
            if item.get("id") == item_id:
                item["status"] = status
                audit("hitl_" + status, item)
                return item
        raise KeyError(item_id)

    def approve_hitl(self, item_id: str) -> Dict[str, Any]:
        return self.resolve_hitl(item_id, "approved")


decision_service = DecisionService()


async def run_decision(reading: Any = None, trigger: str = "api") -> DecisionResult:
    return await decision_service.run(reading, trigger)


__all__ = ["AgentResult", "DispatchResult", "DecisionResult", "DecisionService", "decision_service", "run_decision"]
