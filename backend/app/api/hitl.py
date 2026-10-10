# HITL（人在回路）审批 API：查询待办并批准/拒绝人工介入请求。
from fastapi import APIRouter, HTTPException

from .. import state
from ..decision_service import HitlAlreadyResolvedError, decision_service

router = APIRouter(prefix="/api/hitl", tags=["hitl"])


@router.get("/pending")
def pending():
    # 仅返回仍处于 pending 状态的人工介入单。
    return [x for x in state.hitl if x["status"] == "pending"]


async def update(id, status):
    try:
        # approved 走批准流程；其余状态（如 rejected）走通用解决流程。
        return (
            await decision_service.approve_hitl(id)
            if status == "approved"
            else decision_service.resolve_hitl(id, status)
        )
    except KeyError:
        # 找不到对应单据：404。
        raise HTTPException(status_code=404, detail="HITL request not found")
    except HitlAlreadyResolvedError:
        # 单据已被处理：409 冲突。
        raise HTTPException(status_code=409, detail="HITL request already resolved")


@router.post("/{id}/approve")
async def approve(id: str):
    # 批准：按 approved 状态推进决策服务。
    return await update(id, "approved")


@router.post("/{id}/reject")
async def reject(id: str):
    # 拒绝：按 rejected 状态解决该单据。
    return await update(id, "rejected")
