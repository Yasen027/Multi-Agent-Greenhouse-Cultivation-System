# API 参考

健康、传感器、Agent、决策、HITL、执行器、审计接口可在 FastAPI `/docs` 查看。

核心闭环：

1. `POST /api/sensors/readings` 写入 `SensorReading`（含 `image_url`）。
2. `POST /api/agents/crop-identification/run` 识别作物并生成 `crop_profile`；低置信度时返回 `human_confirmation_required`。
3. `POST /api/agents/run` 并行调度 specialists，返回 `priority_actions`、`human_intervention`、`dispatch` 和审计结果。
4. 只有融合后的命令通过 `hitl_agent` 与 `services.safety()` 才会调用 MQTT dispatch；阻断命令会写入 `state.hitl`。直接调用 `/api/actuators/command` 也会先走同一 `DecisionFusionAgent` 白名单。

设置 `MQTT_BROKER`（可选 `MQTT_ACTUATOR_TOPIC`，默认 `greenhouse/actuators/commands`）后，后端发布的命令由 `edge/mqtt/subscriber.py` 接收；未配置 broker 时返回 `skipped_no_broker`，仍保留审计和模拟运行能力。

作物相关接口：

- `POST /api/agents/crop-identification`：`{image_url, metadata, user_input}`，仅识别。
- `POST /api/agents/crop-identification/analyze`：`{crop, stage, sensor_data_json?, history_json?, weather_json?}`，生成/持久化条件档案。
- `POST /api/agents/crop-identification/confirm`：`{crop, stage?}`，确认 HITL 结果并重新触发后续控制。
- `GET /api/agents/crop-identification/status`：当前档案和触发器状态。
