"""Agent 建议、执行器映射与安全策略的唯一注册表。"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


# 动作规范：一条 recommendation 到执行命令/告警/人工审批的映射定义（不可变）。
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


# 快捷构造器：生成一条执行器开关命令（on/off）的动作规范，默认低风险。
def _command(
    recommendation: str, actuator: str, action: str, risk_level: str = "low"
) -> ActionSpec:
    return ActionSpec(
        recommendation, actuator=actuator, action=action, risk_level=risk_level
    )


# 全局动作注册表：智能体输出的 recommendation 字符串 → 具体动作规范。
# 开关类命令可直接自动下发；高危操作（pH 调整、农药等）与需复核项转为告警/人工审批。
ACTION_REGISTRY: Dict[str, ActionSpec] = {
    "ventilation_on": _command("ventilation_on", "ventilation", "on"),
    "ventilation_off": _command("ventilation_off", "ventilation", "off"),
    "irrigation_on": _command("irrigation_on", "irrigation", "on"),
    "irrigation_off": _command("irrigation_off", "irrigation", "off"),
    "heating_on": _command("heating_on", "heating", "on"),
    "heating_off": _command("heating_off", "heating", "off"),
    "mist_on": _command("mist_on", "mister", "on"),
    "supplemental_light_on": _command("supplemental_light_on", "grow_light", "on"),
    "grow_light_on": _command("grow_light_on", "grow_light", "on"),
    "grow_light_off": _command("grow_light_off", "grow_light", "off"),
    "shade_on": _command("shade_on", "shade", "on"),
    "co2_on": _command("co2_on", "co2", "on"),
    "co2_off": _command("co2_off", "co2", "off"),
    "fan_on": _command("fan_on", "fan", "on"),
    "fan_off": _command("fan_off", "fan", "off"),
# 高危/告警类动作：不直接下发执行器命令，而是生成人工审批项或告警通知。
    "adjust_ph": ActionSpec(
        "adjust_ph",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="pH 调整需要人工审批",
    ),
    "drainage_check": ActionSpec(
        "drainage_check",
        kind="alert",
        risk_level="medium",
        message="调整灌溉前需要检查排水系统",
    ),
    "human_review_soil": ActionSpec(
        "human_review_soil",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="土壤状况需要人工复核",
    ),
    "human_review_temperature": ActionSpec(
        "human_review_temperature",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="温度状况需要人工复核",
    ),
    "human_review_irrigation": ActionSpec(
        "human_review_irrigation",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="灌溉状况需要人工复核",
    ),
    "notify_pest_agent": ActionSpec(
        "notify_pest_agent",
        kind="alert",
        risk_level="medium",
        message="发现病害风险，需要通知病虫害智能体",
    ),
    "co2_enrichment_review": ActionSpec(
        "co2_enrichment_review",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="补充 CO₂ 需要人工复核",
    ),
    "update_stage_thresholds": ActionSpec(
        "update_stage_thresholds",
        kind="alert",
        risk_level="low",
        message="下一控制周期前需要更新生育期阈值",
    ),
    "set_crop_profile": ActionSpec(
        "set_crop_profile",
        kind="alert",
        risk_level="low",
        message="需要更新作物档案",
    ),
    "request_human_confirmation": ActionSpec(
        "request_human_confirmation",
        kind="hitl",
        risk_level="high",
        requires_hitl=True,
        message="作物识别结果需要人工确认",
    ),
    "pesticide_on": ActionSpec(
        "pesticide_on",
        kind="hitl",
        actuator="pesticide",
        action="on",
        risk_level="critical",
        requires_hitl=True,
        message="化学农药控制命令必须经过人工审批",
    ),
}

# 允许自动下发的执行器白名单：仅含无需人工审批且定义了执行器的动作。
ALLOWED_ACTUATORS = frozenset(
    spec.actuator
    for spec in ACTION_REGISTRY.values()
    if spec.actuator and not spec.requires_hitl
)


# 按 recommendation 查找注册表；非字符串输入返回 None，防御异常输入。
def get_action(recommendation: str) -> Optional[ActionSpec]:
    return (
        ACTION_REGISTRY.get(recommendation) if isinstance(recommendation, str) else None
    )


# 将 recommendation 展开为告警/审批字典；未注册的建议按高危 + 强制人工处理。
def action_alert(recommendation: str, agent: str = "agent") -> Dict[str, Any]:
    spec = get_action(recommendation)
    if spec is None:
        return {
            "type": "unknown_recommendation",
            "recommendation": recommendation,
            "agent": agent,
            "risk_level": "high",
            "requires_hitl": True,
            "message": "未注册的智能体建议：" + str(recommendation),
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


# 命令互斥检查：同一批命令中出现物理上互斥的设备组合（加热+通风）时报告冲突。
def command_conflicts(commands: Iterable[Dict[str, Any]]) -> List[str]:
    states = {(c.get("actuator"), c.get("action")) for c in commands}
    conflicts = []
    if ("heating", "on") in states and ("ventilation", "on") in states:
        conflicts.append("加热设备和通风设备不能同时开启")
    return conflicts


# 校验动作命令：执行器必须在白名单内、需人工的命令须给出理由，并叠加互斥检查，去重后返回。
def validate_commands(commands: Iterable[Dict[str, Any]]) -> List[str]:
    reasons = []
    for command in commands or []:
        actuator = command.get("actuator")
        if actuator not in ALLOWED_ACTUATORS:
            reasons.append("执行器未注册或不安全：" + str(actuator))
        if command.get("requires_hitl"):
            reasons.append(command.get("reason") or "控制命令需要人工审批")
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
