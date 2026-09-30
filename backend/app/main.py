from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import sensors,agents,decisions,hitl,actuators,dashboard,ws
from .core.logging import configure_logging
app=FastAPI(title='Greenhouse MAS',version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(sensors.router)
app.include_router(agents.router)
app.include_router(decisions.router)
app.include_router(hitl.router)
app.include_router(actuators.router)
app.include_router(dashboard.router)
app.include_router(ws.router)
@app.on_event('startup')
def startup(): configure_logging()
