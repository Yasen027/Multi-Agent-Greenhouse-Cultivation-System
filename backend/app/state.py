"""进程内运行状态；服务重启后会重新初始化。"""

from .schemas import SensorReading

# 最新读数、决策、人工审批和 Agent 缓存。
latest = SensorReading()
decisions = []
hitl = []
agent_cache = []
# 作物画像与最近一次识别结果。
crop_profile = {"crop": None, "confidence": 0.0, "updated_at": None}
last_crop_identification = {}
# 传感器读数历史（mqtt_runtime 每次插入后截断为最近 100 条）。
history = []
# 天气快照与执行器当前状态。
weather = {}
actuator_state = {}
# 执行器 ACK 流水（最多 100 条）与已确认命令（最多 200 条，按插入序淘汰）。
actuator_acks = []
acknowledged_commands = {}
# 已下发、等待 ACK 的命令及其超时截止时间。
pending_acks = {}
# 执行器连续失败计数（达到阈值会触发熔断）。
actuator_failures = {}
# 熔断状态：True 表示暂停对该执行器下发命令。
actuator_circuits = {}
# 传感器最近值与重复计数（用于检测读数停滞等异常）。
sensor_last_values = {}
sensor_repeat_counts = {}
# 已检测到的传感器与执行器问题（含熔断原因）。
sensor_issues = {}
actuator_issues = {}
# 传感器在线监测的起始时间基准。
sensor_monitor_started_at = None
# 数字孪生最新状态快照：由 MQTT 状态主题或本地孪生同步更新。
digital_twin = {
    "online": False,
    "scenario": None,
    "scenario_name": "等待数字孪生连接",
    "actuators": {},
    "fault": None,
    "updated_at": None,
    "last_sensor_at": None,
}
