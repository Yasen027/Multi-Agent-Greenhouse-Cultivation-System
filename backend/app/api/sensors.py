# 传感器数据接入 API：接收读数写入全局状态与历史，并查询最新读数。
from datetime import datetime, timezone

from fastapi import APIRouter

from .. import state
from ..device_health import record_sensor
from ..schemas import SensorReading
from ..services import audit

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("/readings")
def ingest(reading: SensorReading):
    # 更新最新读数，兼容 Pydantic v1/v2 序列化。
    state.latest = reading
    payload = (
        reading.model_dump() if hasattr(reading, "model_dump") else reading.dict()
    )
    # 历史记录插入头部（最新在前），并裁剪到最多 100 条。
    state.history.insert(0, payload)
    del state.history[100:]
    # 同步刷新数字孪生的最后传感器时间戳（UTC）。
    state.digital_twin["last_sensor_at"] = datetime.now(timezone.utc).isoformat()
    # 记录设备健康与审计事件。
    record_sensor(payload)
    audit("sensor_reading", payload)
    return reading


@router.get("/latest")
def latest():
    # 返回最近一次接收的传感器读数。
    return state.latest
