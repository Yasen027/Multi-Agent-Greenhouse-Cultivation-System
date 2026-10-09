<<<<<<< Updated upstream
import asyncio
=======
"""Agent 运行与作物识别接口。"""

from uuid import uuid4

>>>>>>> Stashed changes
from fastapi import APIRouter

from .. import state
<<<<<<< Updated upstream
from ..schemas import CropTriggerRequest
from ..agents.orchestrator import run_all
from ..agents.decision_agent import decision_agent
from ..agents.hitl_agent import hitl_agent
=======
>>>>>>> Stashed changes
from ..crop_identification_agent import identify_crop
from ..crop_profile import analyze_crop_conditions, analyze_crop_conditions_async
from ..crop_trigger import manager
<<<<<<< Updated upstream
from ..services import audit, safety
from ..tools.actuator_tool import dispatch_commands
from uuid import uuid4
router=APIRouter(prefix='/api/agents',tags=['agents'])
NAMES=['soil','temperature','humidity','pest','irrigation','light_co2','crop_stage','crop_identification']
@router.post('/run')
async def run():
 profile_confidence=float(state.crop_profile.get('confidence') or 1.0)
 if (not state.crop_profile.get('crop') or profile_confidence < 0.7) and state.latest.image_url:
  identification=await asyncio.to_thread(identify_crop, state.latest.image_url, {'device_id':state.latest.device_id})
  state.last_crop_identification=identification
  if not identification['human_intervention']['required']:
   sensor_data=state.latest.model_dump() if hasattr(state.latest,'model_dump') else state.latest.dict()
   state.crop_profile=await analyze_crop_conditions_async(identification['crop'], context={'sensor_data':sensor_data})
   audit('crop_profile_analysis', state.crop_profile)
  else:
   state.hitl.insert(0, {'id':str(uuid4()), 'type':'crop_identification', 'reason':identification['human_intervention']['reason'], 'question':identification['human_intervention']['question_to_human'], 'status':'pending'})
  audit('crop_identification', identification)
 state.agent_cache=list(await run_all(state.latest,state.crop_profile)); commands=decision_agent.fuse(state.agent_cache, {'crop_profile':state.crop_profile,'actuator_state':state.actuator_state,'safety_rules':{'temperature_max':40,'temperature_min':5,'ph_min':4,'ph_max':8}}); check=hitl_agent.evaluate(state.latest,commands); reasons=list(check['reasons']); d={'id':str(uuid4()),'priority_actions':commands,'human_intervention':check['status']!='allow','explanation_for_farmer':'; '.join(reasons) or 'Routine environmental optimization','audit':{'agents':state.agent_cache}}
 gate, safety_reasons = safety(state.latest, commands)
 reasons.extend(safety_reasons)
 low_confidence = [a.get('agent') for a in state.agent_cache if a.get('agent') not in ('crop_identification', 'crop_stage') and float(a.get('confidence') or 1.0) < 0.7]
 if low_confidence: reasons.append('low confidence agents: ' + ','.join(low_confidence))
 crop_pending = bool((state.last_crop_identification or {}).get('human_intervention', {}).get('required'))
 if crop_pending: reasons.append('crop identification requires human confirmation')
 safety_block = check['status'] != 'allow' or gate != 'allow' or bool(low_confidence)
 d['human_intervention'] = safety_block or crop_pending
 d['explanation_for_farmer'] = '; '.join(dict.fromkeys(reasons)) or 'Routine environmental optimization'
 if safety_block:
  d['dispatch'] = {'status': 'blocked_by_safety', 'count': len(commands)}
  state.hitl.insert(0,{'id':str(uuid4()),'decision_id':d['id'],'reason':d['explanation_for_farmer'],'status':'pending'})
 else:
  d['dispatch'] = dispatch_commands(commands)
  if d['dispatch'].get('status') == 'published':
   for command in commands: state.actuator_state[command['actuator']] = command.get('action')
 state.decisions.insert(0,d); audit('decision',d)
 return d
=======
from ..decision_service import decision_service
from ..schemas import CropTriggerRequest
from ..services import audit

router = APIRouter(prefix='/api/agents', tags=['agents'])

# 支持的 Agent 名称
NAMES = ['soil', 'temperature', 'humidity', 'pest', 'irrigation', 'light_co2', 'crop_stage', 'crop_identification']


@router.post('/run')
async def run():
    """运行一次完整决策流程。"""
    result = await decision_service.run(trigger='api')
    return result.to_dict()


>>>>>>> Stashed changes
@router.get('/status')
def status():
    """返回 Agent 缓存状态。"""
    if state.agent_cache:
        return state.agent_cache
    return [{'agent': n, 'status': 'idle', 'confidence': 0.0} for n in NAMES]


@router.post('/crop-identification')
def identify(payload: dict):
    """根据载荷识别作物。"""
    result = identify_crop(payload.get('image_url'), payload.get('metadata'), payload.get('user_input', ''))
    state.last_crop_identification = result
    # 需要人工确认时写入 HITL 队列
    if result['human_intervention']['required']:
        state.hitl.insert(0, {
            'id': str(uuid4()),
            'type': 'crop_identification',
            'reason': result['human_intervention']['reason'],
            'question': result['human_intervention']['question_to_human'],
            'status': 'pending',
        })
    audit('crop_identification', result)
    return result


@router.post('/crop-identification/run')
def run_crop(req: CropTriggerRequest):
    """按触发条件运行作物识别。"""
    if req.interval_hours is not None:
        manager.interval_hours = max(1, req.interval_hours)
    # 未到触发时间则直接返回
    if not manager.should_run(req.reason, req.force, req.reason == 'profile_mismatch'):
        return {
            'triggered': False,
            'reason': 'not_due',
            'status': manager.status(),
            'profile': state.crop_profile,
        }

    result = identify_crop(
        req.image_url or state.latest.image_url,
        req.metadata or {'device_id': state.latest.device_id},
        req.user_input or '',
    )
    state.last_crop_identification = result

    # 需要人工确认或识别失败：写入 HITL 队列
    if result['human_intervention']['required'] or result['crop'] == 'unknown':
        hitl_item = {
            'id': str(uuid4()),
            'reason': result['human_intervention']['reason'],
            'question': result['human_intervention']['question_to_human'],
            'status': 'pending',
            'type': 'crop_identification',
        }
        state.hitl.insert(0, hitl_item)
        audit('crop_identification_pending', {'trigger': req.reason, 'result': result})
        return {
            'triggered': True,
            'reason': 'human_confirmation_required',
            'status': manager.status(),
            'profile': state.crop_profile,
            'identification': result,
            'hitl': hitl_item,
        }

    # 识别成功：分析作物档案并更新状态
    sensor_data = state.latest.model_dump() if hasattr(state.latest, 'model_dump') else state.latest.dict()
    profile = analyze_crop_conditions(result['crop'], context={'sensor_data': sensor_data})
    profile['confidence'] = result['confidence']
    profile['identification_method'] = result['method']
    state.crop_profile = profile
    manager.current_crop = result['crop']
    manager.mark(req.reason)
    audit('crop_identification', {'trigger': req.reason, 'result': result, 'profile': profile})
    return {
        'triggered': True,
        'reason': req.reason,
        'status': manager.status(),
        'profile': profile,
        'identification': result,
    }


@router.post('/crop-identification/analyze')
def analyze_crop(payload: dict):
    """分析作物档案。"""
    crop = payload.get('crop') or (state.crop_profile or {}).get('crop')
    profile = analyze_crop_conditions(crop or 'unknown', payload.get('stage', 'unknown'), payload)
    if profile.get('crop') != 'unknown':
        state.crop_profile = profile
    audit('crop_profile_analysis', profile)
    return profile


@router.post('/crop-identification/confirm')
def confirm_crop(payload: dict):
    """人工确认作物类型。"""
    crop = str(payload.get('crop', 'unknown')).lower().strip()
    supported = ('tomato', 'lettuce', 'strawberry', 'cucumber', 'pepper')
    if crop not in supported:
        return {'status': 'rejected', 'reason': 'unsupported crop'}

    profile = analyze_crop_conditions(crop, payload.get('stage', 'unknown'), payload)
    state.crop_profile = profile
    state.last_crop_identification = {
        'crop': crop,
        'confidence': 1.0,
        'method': 'human_confirmation',
        'human_intervention': {'required': False},
    }
    # 将相关的待处理 HITL 请求标记为已解决
    for item in state.hitl:
        if item.get('type') == 'crop_identification' and item.get('status') == 'pending':
            item['status'] = 'resolved'
    manager.current_crop = crop
    manager.mark('human_confirmation')
    audit('crop_identification_confirmed', profile)
    return {'status': 'confirmed', 'profile': profile}


@router.get('/crop-identification/status')
def crop_status():
    """返回作物识别状态。"""
    return {
        'profile': state.crop_profile,
        'identification': state.last_crop_identification,
        'trigger': manager.status(),
    }
