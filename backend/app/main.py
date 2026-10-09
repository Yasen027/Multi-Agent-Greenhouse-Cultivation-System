"""FastAPI 应用入口与路由挂载。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import actuators, agents, dashboard, decisions, hitl, sensors, ws
from .core.logging import configure_logging

# 创建应用实例
app = FastAPI(title='Greenhouse MAS', version='0.2.0')

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# 挂载各业务路由
app.include_router(sensors.router)
app.include_router(agents.router)
app.include_router(decisions.router)
app.include_router(hitl.router)
app.include_router(actuators.router)
app.include_router(dashboard.router)
app.include_router(ws.router)


@app.on_event('startup')
def startup():
    """应用启动时配置日志。"""
    configure_logging()
