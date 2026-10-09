"""看板、审计、阈值和健康检查接口。"""

from fastapi import APIRouter, Query

from .. import state
from ..services import events

router = APIRouter(tags=["dashboard", "audit", "config"])


@router.get("/api/dashboard/summary")
def summary():
    """返回前端首页需要的最新状态快照。"""
    return {
        "sensor": state.latest,
        "decision": state.decisions[0] if state.decisions else None,
        "pending_hitl": sum(x["status"] == "pending" for x in state.hitl),
        "agents": len(state.agent_cache),
    }


@router.get("/api/audit")
def audit_list():
    """返回全部内存审计事件。"""
    return events()


@router.get("/api/audit/history")
def audit_history(limit: int = Query(100, ge=1, le=1000)):
    """返回最近的指定数量审计事件。"""
    return events()[-limit:]


@router.get("/api/config/thresholds")
def thresholds():
    """返回前端展示用的默认环境阈值。"""
    return {
        "temperature": {"min": 18, "max": 30},
        "humidity": {"min": 50, "max": 80},
        "ph": {"min": 5.5, "max": 7.5},
    }


@router.get("/api/health")
def health():
    """返回服务健康状态。"""
    return {"status": "ok", "version": "0.2.0"}
