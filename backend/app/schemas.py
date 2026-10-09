"""API 请求与传感器数据模型。"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """统一表示温室传感器的一次读数。"""

    device_id: str = "simulator-1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature: float = 24
    humidity: float = 65
    soil_moisture: float = 45
    ph: float = 6.2
    ec: float = 1.5
    light: float = 500
    co2: float = 700
    image_url: Optional[str] = None


class CropTriggerRequest(BaseModel):
    """表示作物识别触发请求及其可选上下文。"""

    reason: str = "manual"
    image_url: Optional[str] = None
    user_input: Optional[str] = None
    metadata: Optional[dict] = None
    force: bool = False
    interval_hours: Optional[int] = None


class ActuatorCommand(BaseModel):
    """表示经过安全层检查的执行器命令。"""

    actuator: str
    action: str
    value: Optional[Union[float, str, bool]] = None
    reason: str = ""
