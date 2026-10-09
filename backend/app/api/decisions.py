"""决策查询接口。"""

from fastapi import APIRouter

from .. import state

router = APIRouter(prefix='/api/decisions', tags=['decisions'])


@router.get('')
def list_decisions():
    """返回全部决策记录。"""
    return state.decisions


@router.get('/latest')
def latest_decision():
    """返回最近一条决策。"""
    if state.decisions:
        return state.decisions[0]
    return {'message': 'no decisions'}
