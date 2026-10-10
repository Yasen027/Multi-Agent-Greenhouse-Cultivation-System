"""API 请求与传感器数据模型。"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """统一表示温室传感器的一次读数。"""

    # 各字段默认值为无真实读数时的初始值；越界值会在 Pydantic 校验阶段被拒绝。
    device_id: str = "simulator-1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature: float = Field(24, ge=-20, le=60)
    humidity: float = Field(65, ge=0, le=100)
    soil_moisture: float = Field(45, ge=0, le=100)
    ph: float = Field(6.2, ge=0, le=14)
    ec: float = Field(1.5, ge=0, le=20)
    light: float = Field(500, ge=0, le=200_000)
    co2: float = Field(700, ge=0, le=10_000)
    image_url: Optional[str] = None


class CropTriggerRequest(BaseModel):
    """表示作物识别触发请求及其可选上下文。"""

    reason: str = "manual"
    image_url: Optional[str] = None
    user_input: Optional[str] = None
    metadata: Optional[dict] = None
    # force=True 可跳过周期限制立即触发识别；interval_hours 可覆盖默认 168 小时（7 天）的识别周期。
    force: bool = False
    interval_hours: Optional[int] = None


class ActuatorCommand(BaseModel):
    """表示经过安全层检查的执行器命令。"""

    actuator: str
    action: str
    value: Optional[Union[float, str, bool]] = None
    reason: str = ""
