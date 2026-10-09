"""WebSocket 实时推送接口。"""

from fastapi import APIRouter, WebSocket

from .. import state

router = APIRouter(tags=['websocket'])


@router.websocket('/ws/updates')
async def updates(socket: WebSocket):
    """接受连接并向客户端推送最新状态快照。"""
    await socket.accept()
    # 统计待人工介入的请求数量
    pending_hitl = sum(x['status'] == 'pending' for x in state.hitl)
    await socket.send_json({
        'sensor': state.latest.model_dump(),
        'decision': state.decisions[0] if state.decisions else None,
        'pending_hitl': pending_hitl,
        'agents': len(state.agent_cache),
    })
