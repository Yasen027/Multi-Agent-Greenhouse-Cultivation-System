# MQTT

所有消息使用 JSON。当前闭环使用以下主题：

| 主题 | 方向 | 用途 |
| --- | --- | --- |
| `greenhouse/sensors/{device_id}` | 数字孪生 → FastAPI | 温度、湿度、土壤湿度、pH、EC、光照、CO₂ |
| `greenhouse/actuators/commands` | FastAPI → 数字孪生 | `{command_id, actuator, action, value, reason}` |
| `greenhouse/actuators/ack` | 数字孪生 → FastAPI | `{command_id, actuator, action, status, error?}` |
| `greenhouse/digital-twin/scenario` | FastAPI → 数字孪生 | `{"scenario":"hot_dry"}` |
| `greenhouse/digital-twin/status` | 数字孪生 → FastAPI | 当前场景、周期、环境、执行器和故障状态 |

每条命令都会生成 `command_id` 并登记 ACK 截止时间；超时会记录为 `status=timeout`。`status=failed` 或超时连续达到阈值后，该执行器进入熔断状态、暂停自动重试并创建一条设备故障 HITL，避免每个控制周期重复刷失败 ACK。

传感器会进行合理范围、连续固定值和离线诊断。传感器超时场景停止发布 sensor topic，但仍发布 twin status；前端分别展示仿真器的“故障注入”和后端独立得出的“系统诊断”。
