# 前端

frontend 使用 Vite 8、React 19、TypeScript 5，后端 API 默认经 Vite 代理到 http://localhost:8000。

## 目录结构

```
frontend/
  vite.config.ts        # React 插件 + /api、/ws 代理 + 构建配置
  tsconfig.json         # strict TS 配置
  index.html            # 应用外壳（#root 挂载点）
  src/
    main.tsx            # 入口：createRoot 挂载 <App/>
    App.tsx             # 外壳：hash 路由（总览/智能体/人工审批/历史审计/温室地图）+ 后端健康指示灯
    style.css           # 全局样式（无第三方 CSS 依赖）
    types.ts            # 与后端 schemas 对齐的统一类型
    services/api.ts     # 统一 API 客户端（dashboard/agents/decisions/HITL/audit）+ ApiError 归一化
    hooks/usePolling.ts # 轮询 Hook（阶段 2：4 秒轮询；页面不可见时暂停）
    utils/format.ts     # 时间 / payload 格式化
    components/         # SensorCard、AgentCard、AlertBanner、DecisionPanel、StatusViews
    pages/              # Dashboard、Agents、HITL、History、GreenhouseMap
```

## 命令

```bash
npm run build     # 生产构建（vite build → dist/）
npm run dev       # 开发服务器（5173，代理 /api → localhost:8000）
npm run preview   # 预览 dist/
npm run typecheck # tsc --noEmit
```

## 数据刷新策略

- 阶段 2 使用 3–5 秒轮询（`POLL_INTERVAL_MS = 4000`，见 `services/api.ts`）；
- 页面不可见时暂停轮询，恢复可见时立即补拉；
- 后续阶段将切换为 `/ws/updates` 的持续 WebSocket 推送（Vite 已配置 `/ws` 代理）。

## 错误处理

所有请求经 `services/api.ts` 的 `request()` 归一化：网络失败、超时、HTTP 错误码（含 FastAPI `detail`）、非 JSON 响应都会转为带中文描述的 `ApiError`；页面通过 `AlertBanner` 展示并可手动重试。后端不可用时顶部健康指示灯变红，各页面显示明确错误。
