"""边缘运行时的 MQTT 命令消费者。

硬件驱动可以为各执行器注入处理器；默认处理器只记录命令，
因此该模块可安全用于仿真环境。
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)
ALLOWED_ACTUATORS = {
    "ventilation",
    "irrigation",
    "heating",
    "mister",
    "grow_light",
    "shade",
    "co2",
    "fan",
}


def handle_command(
    payload: Any, handlers: Optional[Dict[str, Callable[[str, Any], Any]]] = None
) -> Dict[str, Any]:
    command = (
        json.loads(payload) if isinstance(payload, (str, bytes, bytearray)) else payload
    )
    if (
        not isinstance(command, dict)
        or command.get("actuator") not in ALLOWED_ACTUATORS
    ):
        raise ValueError("invalid actuator command")
    actuator, action = command["actuator"], command.get("action", "off")
    value = command.get("value")
    handler = (handlers or {}).get(actuator)
    if handler:
        handler(action, value)
    logger.info("edge command applied: %s/%s", actuator, action)
    return {"status": "applied", "actuator": actuator, "action": action, "value": value}


def subscribe(
    broker: str = "localhost",
    topic: str = "greenhouse/actuators/commands",
    handlers=None,
):
    """进入 Paho 消息循环，并将校验后的命令路由到边缘处理器。"""
    import paho.mqtt.client as mqtt

    client = mqtt.Client()
    client.on_message = lambda _client, _userdata, message: handle_command(
        message.payload, handlers
    )
    client.connect(broker)
    client.subscribe(topic)
    client.loop_forever()
