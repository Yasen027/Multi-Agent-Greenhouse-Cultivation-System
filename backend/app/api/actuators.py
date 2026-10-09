"""执行器指令接口。"""

from uuid import uuid4

from fastapi import APIRouter

from .. import state
from ..agents.decision_agent import decision_agent
from ..schemas import ActuatorCommand
from ..services import audit, safety

router = APIRouter(prefix='/api/actuators', tags=['actuators'])


@router.post('/command')
<<<<<<< Updated upstream
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
=======
def command(cmd: ActuatorCommand):
    """接收执行器指令，经融合与安全检查后下发。"""
    payload = cmd.model_dump() if hasattr(cmd, 'model_dump') else cmd.dict()
    recommendation = payload['actuator'] + '_' + payload['action']
    fused = decision_agent.fuse([{'agent': 'manual_api', 'recommendations': [recommendation]}])

    # 融合未通过：记录告警并拒绝
    if not fused:
        if decision_agent.last_alerts:
            alert = decision_agent.last_alerts[0]
        else:
            alert = {'type': 'actuator_command', 'message': 'command_not_in_fusion_policy'}
        state.hitl.insert(0, {
            'id': str(uuid4()),
            'type': alert['type'],
            'reason': alert['message'],
            'status': 'pending',
        })
        audit('actuator_command_blocked', {'command': payload, 'alert': alert})
        return {
            'status': 'rejected',
            'code': alert['type'],
            'reasons': [alert['message']],
            'alerts': decision_agent.last_alerts,
            'command': cmd,
        }

    # 安全检查
    gate, reasons = safety(state.latest, fused)
    reasons.extend(alert['message'] for alert in decision_agent.last_alerts if alert.get('requires_hitl'))
    reasons = list(dict.fromkeys(reasons))

    if gate != 'allow' or reasons:
        state.hitl.insert(0, {
            'id': str(uuid4()),
            'type': 'actuator_command',
            'reason': '; '.join(reasons),
            'status': 'pending',
        })
        audit('actuator_command_blocked', {
            'command': payload,
            'reasons': reasons,
            'alerts': decision_agent.last_alerts,
        })
        status = gate if gate != 'allow' else 'need_hitl'
        return {
            'status': status,
            'reasons': reasons,
            'alerts': decision_agent.last_alerts,
            'command': cmd,
        }

    # 通过检查：记录并接受
    state.actuator_state[payload['actuator']] = payload.get('action')
    audit('actuator_command', payload)
    return {'status': 'accepted', 'command': cmd}
>>>>>>> Stashed changes
