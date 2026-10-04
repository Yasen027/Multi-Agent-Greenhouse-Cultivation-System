# 作物识别与种植条件分析

传感器/摄像头通过 MQTT（或 `/api/sensors/readings`）更新 `state.latest`。作物识别由 `CropTriggerManager` 在首次启动、换季、换作物、每 168 小时、`profile_mismatch` 或 `force=true` 时触发。

`crop_identification_agent` 优先调用 OpenAI 兼容的 DeepSeek `/chat/completions` 接口：

- `DEEPSEEK_API_KEY`：必填；`DEEPSEEK_BASE_URL` 默认 `https://api.deepseek.com/v1`。
- `DEEPSEEK_MODEL` 默认 `deepseek-chat`；带图片时使用 `DEEPSEEK_VISION_MODEL`（可配置为部署的视觉模型）。
- 请求超时和指数退避重试由 `deepseek_client.py` 处理。无 Key、超时、HTTP 错误或非法 JSON 时自动降级到文件名/元数据关键词匹配，不阻断控制循环。

识别结果固定包含 `crop`、`confidence`、`evidence`、`method` 和 `human_intervention`。置信度低于 0.7 或未知作物会写入 `state.hitl`，不会覆盖当前 `crop_profile`；农户确认后调用确认接口再更新档案。

高置信度识别成功后会调用种植条件分析，生成并持久化到 `config/crop_profiles.json` 的扁平兼容档案：`temperature_min/max`、`humidity_min/max`、`light_min/max`、`co2_min/max`、`ph`、`ec`、`soil_moisture_min/max`，并可附带 `stages`、`water_need` 和 `disease_risks`。现有 specialist agent 继续读取这些键。

接口：

- `POST /api/agents/crop-identification/run`：按触发器执行识别并自动生成档案。
- `POST /api/agents/crop-identification`：仅识别（兼容旧调用）。
- `POST /api/agents/crop-identification/analyze`：按指定作物/生育期单独生成档案。
- `POST /api/agents/crop-identification/confirm`：HITL 确认后写入档案。
- `GET /api/agents/crop-identification/status`：查看档案、最后识别结果和触发器状态。

普通 `POST /api/agents/run` 不会在已有档案且没有新图像时重复识别；它把档案、实时传感器、历史、天气和执行器状态注入 Orchestrator，并行运行 specialist，决策融合后才进行 HITL/safety 审查和 MQTT 下发。
