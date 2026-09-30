from fastapi import APIRouter
from .. import state
from ..schemas import CropTriggerRequest
from ..agents.orchestrator import run_all
from ..agents.decision_agent import decision_agent
from ..agents.hitl_agent import hitl_agent
from ..crop_identification_agent import identify_crop
from ..crop_trigger import manager
from ..services import audit
from uuid import uuid4
router=APIRouter(prefix='/api/agents',tags=['agents'])
NAMES=['soil','temperature','humidity','pest','irrigation','light_co2','crop_stage','crop_identification']
@router.post('/run')
async def run():
 state.agent_cache=list(await run_all(state.latest,state.crop_profile)); commands=decision_agent.fuse(state.agent_cache); check=hitl_agent.evaluate(state.latest,commands); reasons=check['reasons']; d={'id':str(uuid4()),'priority_actions':commands,'human_intervention':check['status']!='allow','explanation_for_farmer':'; '.join(reasons) or 'Routine environmental optimization','audit':{'agents':state.agent_cache}}; state.decisions.insert(0,d); audit('decision',d)
 if d['human_intervention']: state.hitl.insert(0,{'id':str(uuid4()),'decision_id':d['id'],'reason':'; '.join(reasons),'status':'pending'})
 return d
@router.get('/status')
def status(): return state.agent_cache or [{'agent':n,'status':'idle','confidence':0.0} for n in NAMES]
@router.post('/crop-identification')
def identify(payload:dict): return identify_crop(payload.get('image_url'),payload.get('metadata'),payload.get('user_input',''))
@router.post('/crop-identification/run')
def run_crop(req:CropTriggerRequest):
 if req.interval_hours is not None: manager.interval_hours=max(1,req.interval_hours)
 if not manager.should_run(req.reason,req.force,req.reason=='profile_mismatch'): return {'triggered':False,'reason':'not_due','status':manager.status(),'profile':state.crop_profile}
 result=identify_crop(req.image_url or state.latest.image_url,req.metadata or {'device_id':state.latest.device_id}); state.crop_profile=result; manager.current_crop=result['crop']; manager.mark(req.reason); audit('crop_identification',{'trigger':req.reason,'result':result}); return {'triggered':True,'reason':req.reason,'status':manager.status(),'profile':result}
@router.get('/crop-identification/status')
def crop_status(): return {'profile':state.crop_profile,'trigger':manager.status()}
