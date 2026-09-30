from fastapi import APIRouter,WebSocket
from .. import state
router=APIRouter(tags=['websocket'])
@router.websocket('/ws/updates')
async def updates(socket:WebSocket):
 await socket.accept(); await socket.send_json({'sensor':state.latest.model_dump(),'decision':state.decisions[0] if state.decisions else None,'pending_hitl':sum(x['status']=='pending' for x in state.hitl),'agents':len(state.agent_cache)})
