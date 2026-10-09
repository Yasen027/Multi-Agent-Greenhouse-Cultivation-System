"""人工介入（HITL）接口。"""

from fastapi import APIRouter, HTTPException

from .. import state
<<<<<<< Updated upstream
from ..services import audit
router=APIRouter(prefix='/api/hitl',tags=['hitl'])
@router.get('/pending')
def pending(): return [x for x in state.hitl if x['status']=='pending']
def update(id,status):
 for item in state.hitl:
  if item['id']==id:
   item['status']=status; audit('hitl_'+status,item); return item
 raise HTTPException(status_code=404,detail='HITL request not found')
=======
from ..decision_service import decision_service

router = APIRouter(prefix='/api/hitl', tags=['hitl'])


@router.get('/pending')
def pending():
    """返回待处理的 HITL 请求。"""
    return [x for x in state.hitl if x['status'] == 'pending']


def update(id, status):
    """按状态更新 HITL 请求。"""
    try:
        if status == 'approved':
            return decision_service.approve_hitl(id)
        return decision_service.resolve_hitl(id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail='HITL request not found')


>>>>>>> Stashed changes
@router.post('/{id}/approve')
def approve(id: str):
    """批准 HITL 请求。"""
    return update(id, 'approved')


@router.post('/{id}/reject')
def reject(id: str):
    """拒绝 HITL 请求。"""
    return update(id, 'rejected')
