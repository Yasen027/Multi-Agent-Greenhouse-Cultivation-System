"""传感器读数采集接口。"""

from fastapi import APIRouter

from .. import state
from ..schemas import SensorReading
from ..services import audit

router = APIRouter(prefix='/api/sensors', tags=['sensors'])


@router.post('/readings')
def ingest(reading: SensorReading):
    """接收一条传感器读数并写入内存状态。"""
    state.latest = reading
    # 兼容新旧 Pydantic 版本
    payload = reading.model_dump() if hasattr(reading, 'model_dump') else reading.dict()
    state.history.insert(0, payload)
    # 仅保留最近 100 条历史
    del state.history[100:]
    audit('sensor_reading', payload)
    return reading


@router.get('/latest')
def latest():
    """返回最新一条传感器读数。"""
    return state.latest
