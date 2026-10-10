"""比赛场景选择和数字孪生运行状态。"""

from datetime import datetime, timezone
import json
import os

from fastapi import APIRouter, HTTPException

from digital_twin.engine import SCENARIOS

from .. import state
from ..device_health import check_health
from ..local_twin import local_twin
from ..services import audit

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])


@router.get("/scenarios")
def scenarios():
    # 只暴露场景的 id/名称/描述给前端选择。
    return [
        {"id": key, "name": value["name"], "description": value["description"]}
        for key, value in SCENARIOS.items()
    ]


@router.get("/status")
def status():
    # 数字孪生当前状态 = 孪生数据 + 设备诊断 + 最近 ACK 与执行器状态。
    result = dict(state.digital_twin)
    result["diagnostics"] = check_health()
    result["recent_acks"] = state.actuator_acks[:20]
    result["actuator_state"] = dict(state.actuator_state)
    last_sensor_at = result.get("last_sensor_at")
    if last_sensor_at:
        try:
            # Z 后缀换成 UTC 偏移后解析，计算传感器数据年龄（秒）。
            stamp = datetime.fromisoformat(last_sensor_at.replace("Z", "+00:00"))
            result["sensor_age_seconds"] = max(0, (datetime.now(timezone.utc) - stamp).total_seconds())
        except ValueError:
            result["sensor_age_seconds"] = None
    else:
        # 从未收到过传感器数据时年龄未知。
        result["sensor_age_seconds"] = None
    return result


@router.post("/scenario")
async def select_scenario(payload: dict):
    scenario = str(payload.get("scenario", ""))
    # 场景必须在引擎注册的场景集合内，否则 422 拒绝。
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=422, detail="unknown digital-twin scenario")
    # 未配置 MQTT 代理时走本地模拟孪生，否则通过 MQTT 向真实孪生发布场景。
    broker = os.getenv("MQTT_BROKER", "")
    if not broker:
        local_twin.select(scenario)
        local_twin.start()
        audit("digital_twin_scenario_selected", {"scenario": scenario, "transport": "local"})
        return {"status": "simulated_local", "scenario": scenario, "transport": "local"}
    try:
        # 延迟导入 paho：仅在确有 MQTT 环境时引入依赖。
        import paho.mqtt.publish as publish

        # 场景切换通过发布 JSON 消息到数字孪生主题实现，QoS=1 保证至少送达一次。
        topic = os.getenv("MQTT_TWIN_SCENARIO_TOPIC", "greenhouse/digital-twin/scenario")
        publish.single(
            topic,
            json.dumps({"scenario": scenario}, ensure_ascii=False),
            qos=1,
            hostname=broker,
            port=int(os.getenv("MQTT_PORT", "1883")),
        )
    except Exception as exc:
        # 发布失败以 503 返回，并保留原始异常链。
        raise HTTPException(status_code=503, detail=f"failed to publish scenario: {exc}") from exc
    audit("digital_twin_scenario_selected", {"scenario": scenario})
    return {"status": "published", "scenario": scenario, "topic": topic}
