"""FastAPI 的 MQTT 输入适配器：接收孪生传感器、状态与执行器 ACK。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Any

from pydantic import ValidationError

from . import state
from .decision_service import decision_service
from .device_health import (
    check_health,
    record_ack,
    record_invalid_sensor,
    record_sensor,
    reset_health,
)
from .schemas import SensorReading
from .services import audit

logger = logging.getLogger(__name__)


class MqttRuntime:
    def __init__(self) -> None:
        # client 为 paho 连接对象；loop 记录宿主事件循环，供跨线程投递决策任务。
        self.client = None
        self.loop: asyncio.AbstractEventLoop | None = None
        # decision_running 防止上一轮决策未完成时重复触发。
        self.decision_running = False
        # 每秒执行一次健康检查的后台任务句柄。
        self.health_task: asyncio.Task | None = None

    def start(self) -> None:
        # 记录事件循环，供 MQTT 回调线程通过 run_coroutine_threadsafe 投递任务。
        self.loop = asyncio.get_running_loop()
        # 健康检查任务幂等启动：仅在不存在或已结束时创建。
        if self.health_task is None or self.health_task.done():
            self.health_task = asyncio.create_task(self._monitor_health())
        # 未配置 Broker 或已连接时跳过；此时传感器数据由本地孪生回退提供。
        broker = os.getenv("MQTT_BROKER", "")
        if not broker or self.client is not None:
            return
        # 延迟导入 paho，避免未安装依赖时影响无 Broker 环境启动。
        import paho.mqtt.client as mqtt
        # 兼容 paho-mqtt 2.x（需显式 API 版本）与 1.x 两代构造签名。

        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-api"
            )
        except AttributeError:  # paho-mqtt 1.x
            client = mqtt.Client(client_id="greenhouse-api")
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        # 异步连接 + 后台线程收发，不阻塞事件循环；keepalive 30 秒。
        client.connect_async(broker, int(os.getenv("MQTT_PORT", "1883")), keepalive=30)
        client.loop_start()
        self.client = client

    async def stop(self) -> None:
        # 先取消健康检查任务并等待退出，再停止后台线程并断开连接。
        if self.health_task is not None:
            self.health_task.cancel()
            try:
                await self.health_task
            except asyncio.CancelledError:
                pass
            self.health_task = None
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None

    async def _monitor_health(self) -> None:
        while True:
            # 每秒轮询一次设备健康状态（离线/超时/熔断检测）。
            check_health()
            await asyncio.sleep(1)

    def _on_connect(
        self, client, _userdata, _flags, reason_code, _properties=None
    ) -> None:
        # reason_code 非 0 表示连接失败，记录日志后直接返回。
        if reason_code != 0:
            logger.warning("MQTT connection failed: %s", reason_code)
            return
        # 订阅三类主题：传感器读数（通配 +）、执行器 ACK、数字孪生状态，均 QoS 1。
        client.subscribe(
            [
                (os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors/+"), 1),
                (os.getenv("MQTT_ACK_TOPIC", "greenhouse/actuators/ack"), 1),
                (
                    os.getenv(
                        "MQTT_TWIN_STATUS_TOPIC", "greenhouse/digital-twin/status"
                    ),
                    1,
                ),
            ]
        )
        logger.info("backend MQTT input connected")

    def _on_message(self, _client, _userdata, message) -> None:
        # 按主题分流：ACK、孪生状态，其余一律按传感器读数解析。
        try:
            payload = json.loads(message.payload)
            if message.topic == os.getenv("MQTT_ACK_TOPIC", "greenhouse/actuators/ack"):
                self._handle_ack(payload)
            elif message.topic == os.getenv(
                "MQTT_TWIN_STATUS_TOPIC", "greenhouse/digital-twin/status"
            ):
                # 孪生切换场景时重置设备健康记录；随后更新进程内快照并审计。
                if payload.get("scenario") != state.digital_twin.get("scenario"):
                    reset_health()
                state.digital_twin.update(payload)
                audit("digital_twin_status", payload)
            else:
                self._handle_sensor(payload)
        # 任何解析异常都记为被拒绝的载荷并审计，不让回调线程崩溃。
        except Exception as exc:
            logger.warning("invalid MQTT payload on %s: %s", message.topic, exc)
            audit("mqtt_payload_rejected", {"topic": message.topic, "error": str(exc)})

    def _handle_sensor(self, payload: dict[str, Any]) -> bool:
        payload = dict(payload)
        # _twin 是随读数附带的孪生快照字段，先取出以免混入读数模型校验。
        twin = payload.pop("_twin", None)
        # 附带快照同样在场景变化时重置健康状态。
        if twin:
            if twin.get("scenario") != state.digital_twin.get("scenario"):
                reset_health()
            state.digital_twin.update(twin)
        try:
            # 用 Pydantic 模型校验读数；失败则记入 invalid_sensor 并审计后拒绝。
            reading = SensorReading(**payload)
        except ValidationError as exc:
            record_invalid_sensor(exc.errors())
            audit(
                "sensor_reading_rejected",
                {"payload": payload, "errors": exc.errors()},
            )
            return False
        # 兼容 pydantic v1/v2 的序列化接口。
        reading_data = (
            reading.model_dump() if hasattr(reading, "model_dump") else reading.dict()
        )
        # 写入最新读数与内存历史；历史仅保留最近 100 条。
        state.latest = reading
        state.history.insert(0, reading_data)
        del state.history[100:]
        # 更新孪生快照的最后传感器时间戳。
        now = datetime.now(timezone.utc).isoformat()
        state.digital_twin["last_sensor_at"] = now
        # 记录传感器健康并审计该条读数。
        record_sensor(reading_data)
        audit("sensor_reading", reading_data)
        # 通过线程安全接口把决策任务投递回事件循环；decision_running 防止并发触发。
        if self.loop and not self.decision_running:
            self.decision_running = True
            future = asyncio.run_coroutine_threadsafe(
                decision_service.run(reading, trigger="mqtt"), self.loop
            )
            # 决策结束后由回调复位并发标志并记录失败。
            future.add_done_callback(self._decision_done)
        return True

    def _decision_done(self, future) -> None:
        # 先复位并发标志，再检查决策结果并把异常记入审计。
        self.decision_running = False
        try:
            future.result()
        except Exception as exc:
            logger.exception("MQTT-triggered decision failed: %s", exc)
            audit("decision_failed", {"trigger": "mqtt", "error": str(exc)})

    @staticmethod
    def _handle_ack(payload: dict[str, Any]) -> None:
        # 仅把执行器 ACK 交给设备健康跟踪（内部会按 command_id 去重）。
        record_ack(payload)


# 进程级单例：路由与本地孪生共用同一运行时。
mqtt_runtime = MqttRuntime()
