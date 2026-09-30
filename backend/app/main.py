from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from .schemas import SensorReading, ActuatorCommand, CropTriggerRequest
from .agents.orchestrator import run_all
from .agents.decision_agent import decision_agent
from .agents.hitl_agent import hitl_agent
from .crop_identification_agent import identify_crop
from .services import audit,events,safety
from .crop_trigger import manager
from uuid import uuid4
app=FastAPI(title='Greenhouse MAS',version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
latest=SensorReading(); decisions=[]; hitl=[]; agent_cache=[]; crop_profile={'crop':None,'confidence':0.0,'updated_at':None}
@app.get('/api/health')
def health(): return {'status':'ok','version':app.version}
@app.post('/api/sensors/readings')
def ingest(r:SensorReading):
 global latest; latest=r; audit('sensor_reading',r.model_dump()); return r
@app.get('/api/sensors/latest')
def sensors(): return latest
@app.post('/api/agents/crop-identification/run')
def run_crop_identification(req: CropTriggerRequest):
 global crop_profile
 if req.interval_hours is not None: manager.interval_hours=max(1,req.interval_hours)
 if not manager.should_run(req.reason,req.force,req.reason=='profile_mismatch'):
  return {'triggered':False,'reason':'not_due','status':manager.status(),'profile':crop_profile}
 result=identify_crop(req.image_url or latest.image_url, req.metadata or {'device_id':latest.device_id})
 crop_profile=result; manager.current_crop=result['crop']; manager.mark(req.reason); audit('crop_identification',{'trigger':req.reason,'result':result})
 return {'triggered':True,'reason':req.reason,'status':manager.status(),'profile':result}

@app.get('/api/agents/crop-identification/status')
def crop_identification_status(): return {'profile':crop_profile,'trigger':manager.status()}

@app.post('/api/agents/run')
async def run():
 global agent_cache
 agent_cache=[*await run_all(latest, crop_profile)]; commands=[]
 mismatch=any('mismatch' in str(x).lower() for a in agent_cache for x in a.get('findings',[]))
 if manager.should_run(mismatch=mismatch):
  result=identify_crop(latest.image_url, {'device_id':latest.device_id}); manager.current_crop=result['crop']; manager.mark('profile_mismatch' if mismatch else 'scheduled'); audit('crop_identification',{'trigger':'profile_mismatch' if mismatch else 'scheduled','result':result})
 commands=decision_agent.fuse(agent_cache)
 safety_result=hitl_agent.evaluate(latest,commands); gate,reasons=safety_result['status'],safety_result['reasons']; d={'id':str(uuid4()),'priority_actions':commands,'human_intervention':gate!='allow','explanation_for_farmer':'; '.join(reasons) or 'Routine environmental optimization','audit':{'agents':agent_cache}}; decisions.insert(0,d); audit('decision',d)
 if d['human_intervention']: hitl.insert(0,{'id':str(uuid4()),'decision_id':d['id'],'reason':'; '.join(reasons),'status':'pending'})
 return d
@app.post('/api/agents/crop-identification')
def crop_identification(payload: dict):
 return identify_crop(payload.get('image_url'), payload.get('metadata'))

@app.get('/api/agents/status')
def status(): return agent_cache or [{'agent':x,'status':'idle','confidence':0.0} for x in ['soil','temperature','humidity','pest','irrigation','light_co2','crop_stage','crop_identification']]
@app.get('/api/decisions/latest')
def latest_decision(): return decisions[0] if decisions else {'message':'no decisions'}
@app.get('/api/decisions')
def list_decisions(): return decisions
@app.get('/api/hitl/pending')
def pending(): return [h for h in hitl if h['status']=='pending']
@app.post('/api/hitl/{id}/approve')
def approve(id:str):
 for h in hitl:
  if h['id']==id: h['status']='approved'; audit('hitl_approved',h); return h
 return {'error':'not found'}
@app.post('/api/hitl/{id}/reject')
def reject(id:str):
 for h in hitl:
  if h['id']==id: h['status']='rejected'; audit('hitl_rejected',h); return h
 return {'error':'not found'}
@app.post('/api/actuators/command')
def command(c:ActuatorCommand):
 gate,reasons=safety(latest,[c.model_dump()]);
 if gate!='allow': return {'status':gate,'reasons':reasons,'command':c}
 audit('actuator_command',c.model_dump()); return {'status':'accepted','command':c}
@app.get('/api/dashboard/summary')
def summary(): return {'sensor':latest,'decision':decisions[0] if decisions else None,'pending_hitl':len([h for h in hitl if h['status']=='pending']),'agents':len(agent_cache)}
@app.get('/api/audit')
def audit_api(): return events()
@app.websocket('/ws/updates')
async def ws(socket:WebSocket):
 await socket.accept(); await socket.send_json(await summary())

@app.get('/api/audit/history')
def audit_history(limit:int=100): return events()[-max(1,min(limit,1000)):]
@app.get('/api/config/thresholds')
def thresholds(): return {'temperature': {'min':18,'max':30}, 'humidity': {'min':50,'max':80}, 'ph': {'min':5.5,'max':7.5}}
