# FastAPI 应用入口：配置日志与 CORS、挂载路由，并在生命周期中启停 MQTT/本地孪生运行时。
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import actuators, agents, dashboard, decisions, digital_twin, hitl, sensors, ws
from .core.logging import configure_logging
from .local_twin import local_twin
from .mqtt_runtime import mqtt_runtime


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动阶段：初始化日志并启动 MQTT 输入适配器（未配置 Broker 时内部跳过）。
    configure_logging()
    mqtt_runtime.start()
    yield
    # 关闭阶段：先停本地孪生仿真，再停 MQTT 运行时，保证顺序清理。
    await local_twin.stop()
    await mqtt_runtime.stop()


app = FastAPI(title="Greenhouse MAS", version="0.2.0", lifespan=lifespan)
# CORS 全放开，便于前端开发环境跨域调用。
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
# 挂载各业务模块的 API 路由。
app.include_router(sensors.router)
app.include_router(agents.router)
app.include_router(decisions.router)
app.include_router(hitl.router)
app.include_router(actuators.router)
app.include_router(dashboard.router)
app.include_router(digital_twin.router)
app.include_router(ws.router)
