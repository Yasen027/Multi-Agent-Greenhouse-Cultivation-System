"""运行数字孪生并通过 MQTT 形成传感器→决策→执行器→环境闭环。"""

import json
import logging
import os
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from .engine import DigitalTwin

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# 运行参数全部支持环境变量覆盖：MQTT 连接、仿真周期与各主题。
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
INTERVAL = float(os.getenv("TWIN_INTERVAL_SECONDS", "2"))
SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors/digital-twin-1")
COMMAND_TOPIC = os.getenv("MQTT_ACTUATOR_TOPIC", "greenhouse/actuators/commands")
ACK_TOPIC = os.getenv("MQTT_ACK_TOPIC", "greenhouse/actuators/ack")
SCENARIO_TOPIC = os.getenv("MQTT_TWIN_SCENARIO_TOPIC", "greenhouse/digital-twin/scenario")
STATUS_TOPIC = os.getenv("MQTT_TWIN_STATUS_TOPIC", "greenhouse/digital-twin/status")
HEALTH_FILE = Path(os.getenv("TWIN_HEALTH_FILE", "/tmp/digital-twin-health"))


# 创建 MQTT 客户端，兼容 paho-mqtt 2.x 与 1.x 两代回调 API。
def new_client() -> mqtt.Client:
    # 2.x 需要显式指定回调 API 版本；1.x 不支持该参数，捕获异常后回退到默认构造。
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-digital-twin")
    except AttributeError:  # paho-mqtt 1.x
        return mqtt.Client(client_id="greenhouse-digital-twin")


# 主循环：连接 broker、订阅命令/场景主题，并按固定间隔推进仿真并发布传感器与状态。
def run() -> None:
    # 按环境变量指定的场景创建孪生实例，缺省为 normal。
    twin = DigitalTwin(os.getenv("TWIN_SCENARIO", "normal"))
    # 锁保护孪生状态，避免 MQTT 回调线程与主循环并发读写。
    lock = threading.Lock()
    client = new_client()

    # 连接回调：失败时记录错误；成功后订阅命令主题与场景切换主题。
    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        if reason_code != 0:
            logger.error("MQTT connect failed: %s", reason_code)
            return
        client.subscribe([(COMMAND_TOPIC, 1), (SCENARIO_TOPIC, 1)])
        logger.info("digital twin connected to %s:%s", BROKER, PORT)

    # 消息回调：场景主题触发场景切换，命令主题交由孪生处理并回发 ACK；对孪生的操作均在锁内完成。
    def on_message(client, _userdata, message):
        try:
            payload = json.loads(message.payload)
            with lock:
                if message.topic == SCENARIO_TOPIC:
                    twin.select_scenario(payload["scenario"])
                    logger.info("scenario selected: %s", twin.scenario)
                    return
                ack = twin.apply_command(payload)
            # 超时故障下 apply_command 返回 None，此时不发布 ACK（模拟设备无响应）。
            if ack is not None:
                client.publish(ACK_TOPIC, json.dumps(ack, ensure_ascii=False), qos=1)
        # 非法消息仅记录告警并忽略，不中断主循环。
        except Exception as exc:
            logger.warning("ignored invalid MQTT message on %s: %s", message.topic, exc)

    client.on_connect = on_connect
    client.on_message = on_message
    # broker 尚未就绪时每 2 秒重试连接，直到成功。
    while True:
        try:
            client.connect(BROKER, PORT, keepalive=30)
            break
        except OSError as exc:
            logger.warning("waiting for MQTT broker: %s", exc)
            time.sleep(2)
    # 用后台网络线程处理 MQTT 收发，主线程专注仿真推进。
    client.loop_start()
    try:
        # 每周期推进一步仿真，随后发布传感器报文与状态。
        while True:
            with lock:
                twin.step()
                sensor = twin.sensor_payload()
                status = twin.status()
            # 传感器超时故障下 payload 为 None，跳过发布。
            if sensor is not None:
                client.publish(SENSOR_TOPIC, json.dumps(sensor, ensure_ascii=False), qos=1)
            # 状态为保留消息，新订阅者上线即可立即获得最新状态。
            client.publish(STATUS_TOPIC, json.dumps(status, ensure_ascii=False), qos=1, retain=True)
            # Compose 通过文件更新时间确认孪生主循环仍在推进，传感器超时场景也保持健康。
            HEALTH_FILE.touch()
            time.sleep(INTERVAL)
    # 退出时停止网络线程并断开连接。
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run()
