"""Agent 建议、执行器映射与安全策略的唯一注册表。"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ActionSpec:
    recommendation: str
    # 动作类型：执行命令、告警或人工审核。
    kind: str = "command"
    actuator: Optional[str] = None
    action: Optional[str] = None
    risk_level: str = "low"
    requires_hitl: bool = False
    message: str = ""


def _command(
    recommendation: str, actuator: str, action: str, risk_level: str = "low"
) -> ActionSpec:
    return ActionSpec(
        recommendation, actuator=actuator, action=action, risk_level=risk_level
    )


ACTION_REGISTRY: Dict[str, ActionSpec] = {
    "ventilation_on": _command("ventilation_on", "ventilation", "on"),
    "ventilation_off": _command("ventilation_off", "ventilation", "off"),
    "irrigation_on": _command("irrigation_on", "irrigation", "on"),
    "irrigation_off": _command("irrigation_off", "irrigation", "off"),
    "heating_on": _command("heating_on", "heating", "on"),
    "heating_off": _command("heating_off", "heating", "off"),
    "mist_on": _command("mist_on", "mister", "on"),
    "supplemental_light_on": _command("supplemental_light_on", "grow_light", "on"),
    "shade_on": _command("shade_on", "shade", "on"),
    "co2_on": _command("co2_on", "co2", "on"),
    "fan_on": _command("fan_on", "fan", "on"),
    "fan_off": _command("fan_off", "fan", "off"),
    "adjust_ph": ActionSpec(
        "adjust_ph",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="pH adjustment requires human approval",
    ),
    "drainage_check": ActionSpec(
        "drainage_check",
        kind="alert",
        risk_level="medium",
        message="check drainage before changing irrigation",
    ),
    "human_review_soil": ActionSpec(
        "human_review_soil",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="soil condition requires human review",
    ),
    "human_review_temperature": ActionSpec(
        "human_review_temperature",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="temperature condition requires human review",
    ),
    "human_review_irrigation": ActionSpec(
        "human_review_irrigation",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="irrigation condition requires human review",
    ),
    "notify_pest_agent": ActionSpec(
        "notify_pest_agent",
        kind="alert",
        risk_level="medium",
        message="notify pest agent about disease risk",
    ),
    "co2_enrichment_review": ActionSpec(
        "co2_enrichment_review",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="CO2 enrichment requires human review",
    ),
    "update_stage_thresholds": ActionSpec(
        "update_stage_thresholds",
        kind="alert",
        risk_level="low",
        message="update crop-stage thresholds before the next control cycle",
    ),
    "set_crop_profile": ActionSpec(
        "set_crop_profile",
        kind="alert",
        risk_level="low",
        message="crop profile update is required",
    ),
    "request_human_confirmation": ActionSpec(
        "request_human_confirmation",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="crop identification requires human confirmation",
    ),
    "pesticide_on": ActionSpec(
        "pesticide_on",
        kind="hitl",
        actuator="pesticide",
        action="on",
        risk_level="critical",
        requires_hitl=True,
        message="chemical pesticide commands always require human approval",
    ),
}

ALLOWED_ACTUATORS = frozenset(
    spec.actuator
    for spec in ACTION_REGISTRY.values()
    if spec.actuator and not spec.requires_hitl
)


def get_action(recommendation: str) -> Optional[ActionSpec]:
    return (
        ACTION_REGISTRY.get(recommendation) if isinstance(recommendation, str) else None
    )


def action_alert(recommendation: str, agent: str = "agent") -> Dict[str, Any]:
    spec = get_action(recommendation)
    if spec is None:
        return {
            "type": "unknown_recommendation",
            "recommendation": recommendation,
            "agent": agent,
            "risk_level": "high",
            "requires_hitl": True,
            "message": "unregistered recommendation: " + str(recommendation),
        }
    return {
        "type": spec.kind,
        "recommendation": recommendation,
        "agent": agent,
        "actuator": spec.actuator,
        "action": spec.action,
        "risk_level": spec.risk_level,
        "requires_hitl": spec.requires_hitl,
        "message": spec.message or recommendation,
    }


def command_conflicts(commands: Iterable[Dict[str, Any]]) -> List[str]:
    states = {(c.get("actuator"), c.get("action")) for c in commands}
    conflicts = []
    if ("heating", "on") in states and ("ventilation", "on") in states:
        conflicts.append("heating and ventilation cannot both be on")
    return conflicts


def validate_commands(commands: Iterable[Dict[str, Any]]) -> List[str]:
    reasons = []
    for command in commands or []:
        actuator = command.get("actuator")
        if actuator not in ALLOWED_ACTUATORS:
            reasons.append("unregistered or unsafe actuator: " + str(actuator))
        if command.get("requires_hitl"):
            reasons.append(command.get("reason") or "command requires human approval")
    reasons.extend(command_conflicts(commands or []))
    return list(dict.fromkeys(reasons))


__all__ = [
    "ActionSpec",
    "ACTION_REGISTRY",
    "ALLOWED_ACTUATORS",
    "get_action",
    "action_alert",
    "command_conflicts",
    "validate_commands",
]
