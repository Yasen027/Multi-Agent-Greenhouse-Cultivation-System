# Prompt 约定

提示词位于 `backend/prompts/*.md`；`backend/app/prompts` 保留为旧版兼容目录。`PromptLoader` 逐字替换 `{{变量}}`，缺失变量使用 `{}` 或 `unknown`，因此离线/部分数据场景不会把模板标记发给模型。

所有 specialist 通用变量：

- `{{crop}}`、`{{stage}}`：当前作物和生育期。
- `{{crop_profile_json}}`：种植条件档案（必须优先于硬编码阈值）。
- `{{sensor_data_json}}`、`{{history_json}}`、`{{weather_json}}`、`{{actuator_state}}`：实时和上下文数据。
- `{{agents_json}}`、`{{safety_rules}}`：Orchestrator/决策融合专用。

识别提示词还接受 `{{image_data}}`、`{{user_input}}`、`{{context}}`；决策融合提示词必须只描述候选命令，不直接执行。最终执行顺序固定为：specialist → `DecisionFusionAgent.fuse` → `hitl_agent`/`safety` → MQTT。
