from fastapi import APIRouter,HTTPException
from .. import state
from ..decision_service import decision_service
router=APIRouter(prefix='/api/hitl',tags=['hitl'])
@router.get('/pending')
def pending(): return [x for x in state.hitl if x['status']=='pending']
def update(id,status):
 try:
  return decision_service.approve_hitl(id) if status == 'approved' else decision_service.resolve_hitl(id, status)
 except KeyError:
  raise HTTPException(status_code=404,detail='HITL request not found')
@router.post('/{id}/approve')
def approve(id:str): return update(id,'approved')
@router.post('/{id}/reject')
def reject(id:str): return update(id,'rejected')
