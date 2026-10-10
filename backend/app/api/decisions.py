# 决策记录查询 API：读取内存中保存的决策历史。
from fastapi import APIRouter

from .. import state

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("")
def list_decisions():
    # 返回全部决策记录（列表按新旧顺序维护）。
    return state.decisions


@router.get("/latest")
def latest_decision():
    # 头部即最新一条；无记录时给出提示性消息。
    return state.decisions[0] if state.decisions else {"message": "no decisions"}
