"""无 MQTT Broker 时的本地数字孪生回退。"""

from __future__ import annotations

import asyncio
from typing import Any

from digital_twin.engine import DigitalTwin

from . import state
from .device_health import reset_health
from .mqtt_runtime import mqtt_runtime


class LocalTwinRuntime:
    def __init__(self) -> None:
        # 进程内数字孪生引擎实例与后台步进任务句柄。
        self.twin = DigitalTwin()
        self.task: asyncio.Task | None = None

    def select(self, scenario: str) -> None:
        # 切换场景前先重置设备健康状态，随后把孪生最新状态同步到进程内快照。
        reset_health()
        self.twin.select_scenario(scenario)
        state.digital_twin.update(self.twin.status())

    def start(self) -> None:
        # 步进任务只启动一次；同时把当前事件循环记入 mqtt_runtime 供跨线程投递。
        if self.task is None or self.task.done():
            mqtt_runtime.loop = asyncio.get_running_loop()
            self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self.task is None:
            return
        # 取消并等待步进任务退出，保证优雅停机。
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        self.task = None

    def dispatch(self, commands: list[dict[str, Any]]) -> dict[str, Any]:
        acks = []
        # 逐条应用到孪生引擎；返回 ACK 的命令同步交给 MQTT 的 ACK 记录逻辑。
        for command in commands:
            ack = self.twin.apply_command(command)
            if ack is not None:
                mqtt_runtime._handle_ack(ack)
                acks.append(ack)
        # no_response 统计引擎未返回 ACK 的命令数。
        return {
            "status": "simulated_local",
            "count": len(commands),
            "acks": acks,
            "no_response": len(commands) - len(acks),
        }

    async def _run(self) -> None:
        while True:
            # 每 2 秒推进一次仿真，并把新读数喂给 MQTT 传感器处理链路。
            self.twin.step()
            sensor = self.twin.sensor_payload()
            state.digital_twin.update(self.twin.status())
            if sensor is not None:
                mqtt_runtime._handle_sensor(sensor)
            await asyncio.sleep(2)


local_twin = LocalTwinRuntime()
