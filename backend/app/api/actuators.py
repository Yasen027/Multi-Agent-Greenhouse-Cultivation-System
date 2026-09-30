from fastapi import APIRouter
from .. import state
from ..schemas import ActuatorCommand
from ..services import safety,audit
router=APIRouter(prefix='/api/actuators',tags=['actuators'])
@router.post('/command')
def command(cmd:ActuatorCommand):
 gate,reasons=safety(state.latest,[cmd.model_dump()])
 if gate!='allow': return {'status':gate,'reasons':reasons,'command':cmd}
 audit('actuator_command',cmd.model_dump()); return {'status':'accepted','command':cmd}
