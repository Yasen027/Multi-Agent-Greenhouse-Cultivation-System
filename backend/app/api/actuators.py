from fastapi import APIRouter
from .. import state
from ..schemas import ActuatorCommand
from ..services import safety,audit
from uuid import uuid4
from ..agents.decision_agent import decision_agent
router=APIRouter(prefix='/api/actuators',tags=['actuators'])
@router.post('/command')
def command(cmd:ActuatorCommand):
 payload=cmd.model_dump() if hasattr(cmd,'model_dump') else cmd.dict()
 recommendation=payload['actuator']+'_'+payload['action']
 fused=decision_agent.fuse([{'agent':'manual_api','recommendations':[recommendation]}])
 if not fused:
  state.hitl.insert(0, {'id':str(uuid4()), 'type':'actuator_command', 'reason':'command_not_in_fusion_policy', 'status':'pending'})
  audit('actuator_command_blocked', payload)
  return {'status':'rejected','reasons':['command_not_in_fusion_policy'],'command':cmd}
 gate,reasons=safety(state.latest,fused)
 if gate!='allow':
  state.hitl.insert(0, {'id':str(uuid4()), 'type':'actuator_command', 'reason':'; '.join(reasons), 'status':'pending'})
  audit('actuator_command_blocked', {'command':payload,'reasons':reasons})
  return {'status':gate,'reasons':reasons,'command':cmd}
 state.actuator_state[payload['actuator']]=payload.get('action')
 audit('actuator_command',payload); return {'status':'accepted','command':cmd}
