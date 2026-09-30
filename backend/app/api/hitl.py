from fastapi import APIRouter,HTTPException
from .. import state
from ..services import audit
router=APIRouter(prefix='/api/hitl',tags=['hitl'])
@router.get('/pending')
def pending(): return [x for x in state.hitl if x['status']=='pending']
def update(id,status):
 for item in state.hitl:
  if item['id']==id:
   item['status']=status; audit('hitl_'+status,item); return item
 raise HTTPException(status_code=404,detail='HITL request not found')
@router.post('/{id}/approve')
def approve(id:str): return update(id,'approved')
@router.post('/{id}/reject')
def reject(id:str): return update(id,'rejected')
