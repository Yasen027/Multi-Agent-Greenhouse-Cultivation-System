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
  alert = decision_agent.last_alerts[0] if decision_agent.last_alerts else {'type':'actuator_command','message':'command_not_in_fusion_policy'}
  state.hitl.insert(0, {'id':str(uuid4()), 'type':alert['type'], 'reason':alert['message'], 'status':'pending'})
  audit('actuator_command_blocked', {'command':payload,'alert':alert})
  return {'status':'rejected','code':alert['type'],'reasons':[alert['message']],'alerts':decision_agent.last_alerts,'command':cmd}
 gate,reasons=safety(state.latest,fused)
 reasons.extend(alert['message'] for alert in decision_agent.last_alerts if alert.get('requires_hitl'))
 reasons=list(dict.fromkeys(reasons))
 if gate!='allow' or reasons:
  state.hitl.insert(0, {'id':str(uuid4()), 'type':'actuator_command', 'reason':'; '.join(reasons), 'status':'pending'})
  audit('actuator_command_blocked', {'command':payload,'reasons':reasons,'alerts':decision_agent.last_alerts})
  return {'status':gate if gate!='allow' else 'need_hitl','reasons':reasons,'alerts':decision_agent.last_alerts,'command':cmd}
 state.actuator_state[payload['actuator']]=payload.get('action')
 audit('actuator_command',payload); return {'status':'accepted','command':cmd}
