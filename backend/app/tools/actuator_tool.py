"""受安全门保护的 MQTT 执行器分发器兼容包装。"""

from .actuator_dispatch import dispatch_commands

__all__ = ["dispatch_commands"]
