"""将已经通过安全检查的命令尽力转发到 MQTT。"""

import json
import logging
import os
from typing import Any, Dict, Iterable

from ..action_registry import ALLOWED_ACTUATORS
from ..device_health import prepare_commands, record_ack

logger = logging.getLogger(__name__)


def dispatch_commands(commands: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    # 分发执行器命令：白名单校验 → 健康/熔断过滤 → 有 Broker 走 MQTT、无 Broker 回退本地孪生。
    commands = list(commands or [])
    # 纵深防御：任一命令的执行器不在白名单内则整批拒绝。
    unsafe = [
        command
        for command in commands
        if command.get("actuator") not in ALLOWED_ACTUATORS
    ]
    if unsafe:
        return {"status": "blocked_unsafe_actuator", "count": 0, "rejected": unsafe}
    # 空命令列表直接返回，无需后续处理。
    broker = os.getenv("MQTT_BROKER", "")
    if not commands:
        return {"status": "nothing_to_dispatch", "count": 0}
    # prepare_commands 生成 command_id 并登记等待 ACK；处于熔断状态的执行器命令被抑制。
    commands, suppressed = prepare_commands(commands)
    if not commands:
        # 全部命令被抑制说明对应执行器已熔断。
        return {"status": "circuit_open", "count": 0, "suppressed": suppressed}
    # 未配置 Broker 时回退到进程内本地孪生执行。
    if not broker:
        from ..local_twin import local_twin

        result = local_twin.dispatch(commands)
        result["command_ids"] = [command["command_id"] for command in commands]
        if suppressed:
            result["suppressed"] = suppressed
        return result
    try:
        import paho.mqtt.publish as publish

        # 有 Broker：批量发布全部命令，QoS 1 保证至少一次送达。
        topic = os.getenv("MQTT_ACTUATOR_TOPIC", "greenhouse/actuators/commands")
        messages = []
        for command in commands:
            messages.append(
                {
                    "topic": topic,
                    "payload": json.dumps(command, ensure_ascii=False),
                    "qos": 1,
                }
            )
        publish.multiple(
            messages,
            hostname=broker,
            port=int(os.getenv("MQTT_PORT", "1883")),
        )
        result = {
            "status": "published",
            "count": len(commands),
            "topic": topic,
            "command_ids": [command["command_id"] for command in commands],
        }
        if suppressed:
            result["suppressed"] = suppressed
        return result
    # 发布异常：把每条命令记为 failed ACK（计入失败次数、可能触发熔断），并返回 dispatch_failed。
    except Exception as exc:
        logger.warning("MQTT dispatch failed: %s", exc)
        for command in commands:
            record_ack({**command, "status": "failed", "error": str(exc)})
        return {"status": "dispatch_failed", "count": len(commands), "error": str(exc)}
