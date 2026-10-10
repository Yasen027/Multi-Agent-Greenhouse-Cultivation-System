"""边缘运行时的 MQTT 命令消费者。

硬件驱动可以为各执行器注入处理器；默认处理器只记录命令，
因此该模块可安全用于仿真环境。
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)
# 执行器白名单：仅这些名称允许通过 MQTT 下发控制命令，未命中一律拒绝。
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


# 解析并校验一条执行器命令，路由到对应处理器并返回执行确认。
def handle_command(
    payload: Any, handlers: Optional[Dict[str, Callable[[str, Any], Any]]] = None
) -> Dict[str, Any]:
    # 字符串/字节负载先按 JSON 解析，已是字典则直接使用。
    command = (
        json.loads(payload) if isinstance(payload, (str, bytes, bytearray)) else payload
    )
    if (
        # 命令必须是字典且执行器在白名单内，否则视为非法命令抛出异常。
        not isinstance(command, dict)
        or command.get("actuator") not in ALLOWED_ACTUATORS
    ):
        raise ValueError("invalid actuator command")
    # 动作缺省为 off；value 可选，具体语义交由处理器解释。
    actuator, action = command["actuator"], command.get("action", "off")
    value = command.get("value")
    # 未注册处理器的执行器仅记录日志、不做实际控制，因此可在仿真环境安全运行。
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
    # 延迟导入 Paho，未安装 MQTT 库的环境也能 import 本模块。
    import paho.mqtt.client as mqtt

    # 连接 broker、订阅命令主题后进入阻塞式消息循环，收到的每条消息交给 handle_command 校验路由。
    client = mqtt.Client()
    client.on_message = lambda _client, _userdata, message: handle_command(
        message.payload, handlers
    )
    client.connect(broker)
    client.subscribe(topic)
    client.loop_forever()
