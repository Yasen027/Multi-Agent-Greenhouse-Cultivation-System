"""进程内运行状态；服务重启后会重新初始化。"""

from .schemas import SensorReading

# 最新读数、决策、人工审批和 Agent 缓存。
latest = SensorReading()
decisions = []
hitl = []
agent_cache = []
crop_profile = {"crop": None, "confidence": 0.0, "updated_at": None}
last_crop_identification = {}
history = []
weather = {}
actuator_state = {}
