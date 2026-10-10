# 执行器指令路由：接收指令，经决策融合与安全检查后下发到设备。
from uuid import uuid4

from fastapi import APIRouter

from .. import state
from ..agents.decision_agent import decision_agent
from ..schemas import ActuatorCommand
from ..services import audit, safety
from ..tools.actuator_dispatch import dispatch_commands

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


@router.post("/command")
def command(cmd: ActuatorCommand):
    """接收执行器指令，经融合与安全检查后下发。"""
    payload = cmd.model_dump() if hasattr(cmd, "model_dump") else cmd.dict()
    # 把「执行器+动作」拼成动作注册表使用的建议标识，例如 "fan_on"。
    recommendation = payload["actuator"] + "_" + payload["action"]
    fused = decision_agent.fuse(
        [{"agent": "manual_api", "recommendations": [recommendation]}]
    )

    # 融合未通过：记录告警并拒绝
    if not fused:
        if decision_agent.last_alerts:
            alert = decision_agent.last_alerts[0]
        else:
            alert = {
                "type": "actuator_command",
                "message": "command_not_in_fusion_policy",
            }
        state.hitl.insert(
            0,
            {
                "id": str(uuid4()),
                "type": alert["type"],
                "reason": alert["message"],
                "status": "pending",
            },
        )
        audit("actuator_command_blocked", {"command": payload, "alert": alert})
        return {
            "status": "rejected",
            "code": alert["type"],
            "reasons": [alert["message"]],
            "alerts": decision_agent.last_alerts,
            "command": cmd,
        }

    # 安全检查
    gate, reasons = safety(state.latest, fused)
    reasons.extend(
        alert["message"]
        for alert in decision_agent.last_alerts
        if alert.get("requires_hitl")
    )
    # 按插入顺序去重拒绝理由，避免同一原因重复出现。
    reasons = list(dict.fromkeys(reasons))

    # 安全检查未放行或有任何拒绝理由：写入 HITL 待办而非下发。
    if gate != "allow" or reasons:
        state.hitl.insert(
            0,
            {
                "id": str(uuid4()),
                "type": "actuator_command",
                "reason": "; ".join(reasons),
                "status": "pending",
            },
        )
        audit(
            "actuator_command_blocked",
            {
                "command": payload,
                "reasons": reasons,
                "alerts": decision_agent.last_alerts,
            },
        )
    # 安全门结果是 allow 但仍有理由时，统一按 need_hitl 状态返回。
        status = gate if gate != "allow" else "need_hitl"
        return {
            "status": status,
            "reasons": reasons,
            "alerts": decision_agent.last_alerts,
            "command": cmd,
        }

    # 通过检查：发布到 MQTT；设备最终结果以后续 ACK 为准。
    dispatch = dispatch_commands(fused)
    if dispatch["status"] == "dispatch_failed":
        audit("actuator_command_failed", {"command": payload, "dispatch": dispatch})
        return {"status": "dispatch_failed", "command": cmd, "dispatch": dispatch}
    audit("actuator_command", {"command": payload, "dispatch": dispatch})
    return {"status": "accepted", "command": cmd, "dispatch": dispatch}
