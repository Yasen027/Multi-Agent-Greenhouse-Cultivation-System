"""Pydantic 数据模型定义。

统一传感器读数、作物触发请求与执行器指令的请求/响应结构。
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """单条温室传感器读数。"""
    # 设备标识，默认模拟器
    device_id: str = 'simulator-1'
    # 采样时间戳，默认取当前 UTC 时间
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # 空气温度（℃）
    temperature: float = 24
    # 空气湿度（%）
    humidity: float = 65
    # 土壤湿度（%）
    soil_moisture: float = 45
    # 土壤酸碱度
    ph: float = 6.2
    # 电导率（mS/cm）
    ec: float = 1.5
    # 光照强度（μmol/m²/s 或 lux）
    light: float = 500
    # 二氧化碳浓度（ppm）
    co2: float = 700
    # 可选图像地址，用于作物识别
    image_url: Optional[str] = None


class CropTriggerRequest(BaseModel):
    """手动触发作物识别的请求体。"""
    reason: str = 'manual'
    image_url: Optional[str] = None
    user_input: Optional[str] = None
    metadata: Optional[dict] = None
    force: bool = False
    interval_hours: Optional[int] = None


class ActuatorCommand(BaseModel):
    """执行器控制指令。"""
    actuator: str
    action: str
    value: Optional[Union[float, str, bool]] = None
    reason: str = ''
