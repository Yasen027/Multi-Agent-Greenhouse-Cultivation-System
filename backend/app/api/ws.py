# WebSocket 接口：客户端连接后立即推送一次当前系统状态快照。
from fastapi import APIRouter, WebSocket

from .. import state

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/updates")
async def updates(socket: WebSocket):
    # 接受连接后推送一次性快照：传感器读数、最新决策、待办数与 Agent 数。
    await socket.accept()
    await socket.send_json(
        {
            "sensor": state.latest.model_dump(),
            "decision": state.decisions[0] if state.decisions else None,
            "pending_hitl": sum(x["status"] == "pending" for x in state.hitl),
            "agents": len(state.agent_cache),
        }
    )
