# 阶段 1 实施状态：可重复运行环境

> 日期：2026-10-06 · 分支：`intall` · 状态：阶段 1 验收标准全部达成

## 1. 验收标准核对

| 验收项 | 结果 | 证据 |
|---|---|---|
| 干净环境可导入 `backend.app.main` | ✅ 通过 | 新建 `.verify-venv`（Python 3.12.14）→ `pip install -r requirements.txt` → `import backend.app.main` 成功（`app = Greenhouse MAS 0.2.0`） |
| pytest 进入收集阶段，不再因缺依赖直接失败 | ✅ 通过 | `python -m pytest -q` → **3 passed, 6 warnings**（收集 2 个测试文件共 3 个用例） |
| 统一测试命令 | ✅ 已固定 | 根目录执行 `.venv\Scripts\python.exe -m pytest -q`，`pytest.ini` 固定 `testpaths`/`pythonpath` |
| FastAPI / Pydantic / pytest / paho-mqtt 同一解释器导入 | ✅ 通过 | `.venv\Scripts\python.exe` 下四者版本：0.142.2 / 2.13.5 / 9.1.1 / 2.1.0 |
| 所有开发人员同一套启动与测试方式 | ✅ 已文档化 | [setup.md](setup.md) 为唯一入口文档 |

## 2. 环境基线（已固定）

| 组件 | 固定版本 | 备注 |
|---|---|---|
| Python | **3.12.14**（要求 3.12.x） | 旧环境为系统 Python 3.9.13（已 EOL），阶段 1 起固定为 3.12 |
| `.venv` | 项目根目录，基于 3.12.14 | 用 `py -3.12 -m venv .venv` 重建 |
| requirements.txt | fastapi 0.142.2 / uvicorn[standard] 0.54.0 / pydantic 2.13.5 / httpx 0.28.1 / pytest 9.1.1 / paho-mqtt 2.1.0 | 原文件未锁版本，现全部 `==` 锁定 |
| Node.js | ≥ 20.19（本机 24.21.0） | frontend `engines` 已声明 |
| pnpm | 11.7.0 | `packageManager` 字段已声明 |
| frontend/package.json | react 19.3.0 / vite 8.3.3 / @vitejs/plugin-react 6.1.2 / typescript 5.9.3 | 原为 `latest`，现全部精确锁定 |
| pnpm-lock.yaml | 已生成并纳入版本管理 | 原无锁文件 |
| pytest.ini | 新增：`testpaths = tests`、`pythonpath = .` | 消除工作目录差异 |
| .gitignore | 新增：忽略 .venv/__pycache__/.pytest_cache/node_modules/dist/greenhouse.db 等 | 原仓库无 .gitignore |
| Docker 基线 | backend→`python:3.12-slim`；frontend→`node:22-alpine`+pnpm | 与本地固定版本对齐 |

## 3. 可用入口

### 3.1 后端（已验证）

| 入口 | 命令 / 路径 | 状态 |
|---|---|---|
| FastAPI 应用 | `python -m uvicorn backend.app.main:app --reload --port 8000` | ✅ 启动实测通过，`/api/health` 200 |
| 健康检查 | `GET /api/health` | ✅ `{"status":"ok","version":"0.2.0"}` |
| 看板汇总 | `GET /api/dashboard/summary` | ✅ 200（实测） |
| 主业务闭环 | `POST /api/agents/run` | ✅ 被 tests/test_crop_pipeline.py 覆盖（离线链路） |
| 其余路由 | sensors / agents / decisions / hitl / actuators / dashboard / ws | ✅ 随 app 挂载，接口文档见 `/docs` |
| 测试 | `.venv\Scripts\python.exe -m pytest -q`（根目录）或 `scripts\test.ps1`（任意目录） | ✅ 3 passed |
| 仿真脚本 | `python scripts/run_simulation.py` | ⚠️ 需后端已运行（未在本阶段实测） |
| 统一脚本 | `scripts/setup.ps1` / `test.ps1` / `dev-backend.ps1` / `dev-frontend.ps1` | ✅ 新增；test 与 dev-backend 已实测 |

### 3.2 前端（已验证）

| 入口 | 命令 | 状态 |
|---|---|---|
| 开发服务器 | `cd frontend && pnpm dev` | ✅ http://localhost:5173 实测 200 |
| 生产构建 | `cd frontend && pnpm build` | ✅ vite 8.3.3 构建成功，产出 `frontend/dist` |
| 锁版安装 | `cd frontend && pnpm install` | ✅ 实测成功 |

### 3.3 边缘侧（未实测）

`edge/mqtt/publisher.py`（HTTP 模拟传感器）、`edge/mqtt/subscriber.py`（MQTT 订阅）、`edge/mqtt/command_handler.py`（命令校验）。依赖 `edge/requirements.txt`（paho-mqtt），与主 venv 不冲突。

## 4. 占位模块（当前仅有占位符或空骨架）

| 位置 | 内容 |
|---|---|
| `backend/app/core/config.py`、`constants.py`、`security.py` | 配置/常量/安全层占位 |
| `backend/app/agents/memory_agent.py`、`pest_agent.py` | 记忆、病虫害 Agent 占位 |
| `backend/app/agents/graph/workflow.py`、`edges.py`、`state.py` | 图式工作流占位 |
| `backend/app/db/models/*`、`db/migrations/` | ORM 模型/迁移占位（实际写入仍在 `db/session.py` 原生 sqlite3） |
| `backend/app/tools/image_tool.py`、`rag_tool.py`、`sensor_tool.py`、`weather_tool.py` | 工具占位 |
| `backend/tests/unit`、`integration`、`simulation`、`prompt_eval` | 空目录（测试待补充） |
| `edge/drivers/*`、`edge/control/*`、`edge/inference/*` | 传感器驱动/执行器/推理占位 |
| `frontend/src/pages/*`、`components/*`、`services/api.ts`、`App.tsx` | 页面/组件/API 封装占位 |
| `frontend/Dockerfile` | 占位（compose 内联命令替代） |
| `scripts/calibrate_sensors.py`、`eval_agents.py`、`seed_knowledge.py` | 脚本占位 |
| `config/agents.yaml`、`devices.yaml`、`thresholds.yaml` | 配置占位（未被代码读取） |
| `deploy/*`（mosquitto/nginx 配置、docker/grafana/k8s 目录） | 部署扩展占位 |
| `notebooks/*.ipynb` | 实验 Notebook 占位 |

## 5. 已知限制

1. **状态在进程内存**：`state.py` 的最新读数/决策/HITL/档案重启即失；SQLite 仅存审计（`greenhouse.db`）。
2. **专家 Agent 为本地规则**：specialists 加载 Prompt 但不调用 DeepSeek；仅作物识别/档案分析走模型。
3. **配置非单一事实来源**：`config/*.yaml` 多数未被读取，规则写死在 Python 中。
4. **WebSocket 仅发一次快照**：`ws.py` 建连后无持续推送。
5. **前端硬编码后端地址**：`src/main.tsx` 直连 `http://localhost:8000`（代理已在 vite 配置好，但代码未用相对路径）。
6. **`POST /api/actuators/command` 只更新状态/审计**，不直接 MQTT 下发（设计如此，见 README 控制链说明）。
7. **HITL approve 后不自动重跑决策**。
8. **crop_profiles.json 会被运行/测试写回**（`_save_profile`），属运行产物，注意提交时排除误改。
9. **仓库卫生**：`__pycache__/*.pyc` 曾被提交进 git 并持续产生 diff（.gitignore 已加，但已跟踪文件需手动 `git rm -r --cached` 清理）；当前分支名 `intall`（疑似 `install` 拼写）；根目录游离文件 `tmpx_6va4i_cacert.pem`（TLS 调试遗留，可删）。
10. **DSH 沙箱限制（仅本会话环境）**：受限模式下 pip/pnpm 的临时目录写入被拒（需完全权限执行安装）；`.pytest_cache` 在受限模式曾被拒访问（完全权限下正常，pytest 结果不受影响）。正常开发机均无此问题。

## 6. 初始问题清单

| 编号 | 级别 | 问题 | 建议 |
|---|---|---|---|
| I-01 | P2 | `datetime.utcnow()` 弃用（schemas.py / crop_profile.py / crop_trigger.py / services.py） | 迁移 `datetime.now(datetime.UTC)` 等时区感知写法 |
| I-02 | P2 | FastAPI `@app.on_event('startup')` 弃用（main.py） | 迁移 lifespan 处理器 |
| I-03 | P3 | starlette TestClient 提示 `httpx` 即将弃用 | 后续按 FastAPI 官方指引迁移 `httpx2`，暂不影响使用 |
| I-04 | P2 | 前端硬编码 `localhost:8000` | 改用相对路径走 vite 代理 |
| I-05 | P3 | `backend/tests/*` 四个子目录为空 | 补充单元/集成/仿真测试时填充 |
| I-06 | P3 | git 跟踪 `__pycache__`（33 个 .pyc 持续产生 diff） | `git rm -r --cached --ignore-unmatch` 清理后提交 |
| I-07 | P3 | 分支名 `intall` | 与团队确认后改名为 `install` 或合入主分支 |
| I-08 | P3 | 根目录游离文件 `tmpx_6va4i_cacert.pem` | 确认无用后删除 |
| I-09 | P3 | 测试运行会写回 `config/crop_profiles.json` | 接受为现状或为测试增加隔离（如 CROP_PROFILE_PATH 指向临时文件） |
| I-10 | P3 | Docker 容器路径未在本阶段实测 | 阶段 2 联调 `docker compose up` |
| I-11 | P3 | 前端 `pnpm dev` 默认仅绑定 localhost | 需要局域网访问时用 `pnpm dev -- --host` |

> 当前测试基线无失败用例（3/3 通过）；运行期可见 6 条警告与上表 I-01～I-03 对应，已全部记录。

## 7. 阶段 1 交付物索引

- 可重复启动说明：[setup.md](setup.md)（同时更新了 [testing.md](testing.md)、[deployment.md](deployment.md)）
- 可执行测试命令：`.venv\Scripts\python.exe -m pytest -q`（根目录）
- 初始问题清单：本文第 6 节
- 本状态文档：本文
