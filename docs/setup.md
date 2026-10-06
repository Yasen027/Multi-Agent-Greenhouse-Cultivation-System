# 环境搭建与启动（阶段 1 · 可重复运行环境）

> 目标：所有开发人员使用同一套 Python / Node 环境、同一套启动与测试方式，避免系统解释器、依赖版本和工作目录差异影响开发。
>
> 验证基线：**Python 3.12.14**、**Node.js 24.21.0**、**pnpm 11.7.0**（Windows 10/11，2026-10-06 实测通过）。

## 0. 推荐：统一脚本（任意目录可用）

为消除“在哪个目录执行”的差异，根目录提供四个固定脚本，**从任意目录**执行即可：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1        # 创建 .venv 并安装固定依赖
powershell -ExecutionPolicy Bypass -File scripts\test.ps1         # 统一测试命令
powershell -ExecutionPolicy Bypass -File scripts\dev-backend.ps1  # 启动后端（Ctrl+C 停止）
powershell -ExecutionPolicy Bypass -File scripts\dev-frontend.ps1 # 启动前端（Ctrl+C 停止）
```

> 提示：`dev-frontend.ps1` 依赖 `pnpm` 在 PATH 中；其余脚本只依赖 venv 内的解释器。
> 下面第 2～5 节是等效的原始命令，便于理解与排查。

## 1. 前置要求

| 工具 | 版本要求 | 说明 |
|---|---|---|
| Python | **3.12.x**（3.12.14 已验证） | 系统自带 3.9 已 EOL，不再使用 |
| Node.js | **≥ 20.19**（24.21.0 已验证） | vite 8 的最低要求 |
| pnpm | **11.x**（11.7.0 已验证） | 前端统一使用 pnpm，锁文件已入库 |
| Docker（可选） | 任意较新版本 | 备用容器启动方式 |

## 2. 后端环境（一次性初始化）

**在项目根目录执行**（PowerShell）：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- `requirements.txt` 已固定到精确版本：fastapi 0.142.2、uvicorn[standard] 0.54.0、pydantic 2.13.5、httpx 0.28.1、pytest 9.1.1、paho-mqtt 2.1.0。
- 干净环境按上面两条命令即可复现（2026-10-06 用全新 venv 实测：安装成功、`import backend.app.main` 成功、pytest 3 passed）。

## 3. 统一测试命令

**在项目根目录执行**：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- `pytest.ini` 固定了 `testpaths = tests` 与 `pythonpath = .`（backend 包任意位置可导入）。
- 注意：pytest 9 只在项目根目录运行时采用 `testpaths`，请统一在根目录执行本命令。
- 当前基线：**3 passed**（详见 [implementation-status.md](implementation-status.md)）。

## 4. 启动后端

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

验证：<http://localhost:8000/api/health> 返回 `{"status":"ok","version":"0.2.0"}`；接口文档 <http://localhost:8000/docs>。

## 5. 前端环境与启动

```powershell
cd frontend
pnpm install        # 按 pnpm-lock.yaml 锁版安装
pnpm dev            # 开发服务器 http://localhost:5173
pnpm build          # 生产构建，产出 frontend/dist
```

- `package.json` 已固定精确版本：react 19.3.0、react-dom 19.3.0、vite 8.3.3、@vitejs/plugin-react 6.1.2、typescript 5.9.3、@types/react(-dom) 19.3.0。
- `pnpm-lock.yaml` 已入库，保证所有机器解析结果一致。
- `vite.config.ts` / `tsconfig.json` 已从占位文件改为可用配置（React 插件 + `/api`、`/ws` 代理到 localhost:8000）。

## 6. 备用：Docker 启动

```powershell
docker compose up
```

- api 服务：`python:3.12-slim`，容器内 `pip install -r requirements.txt` + uvicorn。
- frontend 服务：`node:22-alpine`，corepack 启用 pnpm 后按锁文件安装并启动 vite。
- 说明：容器路径与第 2/5 节的本机路径等价；阶段 1 仅验证了本机路径，容器路径待后续联调。

## 7. 约定：命令在项目根目录执行（或用统一脚本）

后端导入链（`backend.app.main`、`greenhouse.db` 路径等）以项目根目录为工作目录。为消除“工作目录差异”：

- 第 2～5 节的原始命令**一律在项目根目录执行**；
- 或直接使用第 0 节的统一脚本，脚本内部会自动切换到项目根目录，任何目录下都可运行（2026-10-06 已在子目录实测）。

## 8. 本机（DSH 沙箱）环境备注

本仓库文档面向所有开发人员；若在本会话的 DSH 沙箱中操作，另有两处环境差异（不影响正常开发机）：

- DSH 受限沙箱会拒绝 pip/pnpm 在临时目录（`mkdtemp`、`_tmp_*` 探测文件）内的写入，安装依赖需在「完全权限」下执行；正常开发机无此限制。
- 本机 PowerShell 的 HTTPS（Schannel）不可用；pip 与 node 自带 TLS 栈，不受影响。

详细记录见 [implementation-status.md](implementation-status.md)。
