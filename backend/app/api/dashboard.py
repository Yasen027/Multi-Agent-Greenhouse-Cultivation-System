"""看板、审计、阈值和健康检查接口。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from .. import state
from ..device_health import check_health
from ..services import events

router = APIRouter(tags=["dashboard", "audit", "config"])


@router.get("/api/dashboard/summary")
def summary():
    """返回前端首页需要的最新状态快照。"""
    twin = dict(state.digital_twin)
    twin["diagnostics"] = check_health()
    if twin.get("last_sensor_at"):
        try:
            # 把 ISO 时间串末尾的 Z 换成 UTC 偏移再解析，避免兼容性问题。
            stamp = datetime.fromisoformat(twin["last_sensor_at"].replace("Z", "+00:00"))
            # 传感器数据年龄，最小为 0，防止时钟偏差产生负数。
            twin["sensor_age_seconds"] = max(0, (datetime.now(timezone.utc) - stamp).total_seconds())
        except ValueError:
            # 时间格式非法时年龄置空而非报错。
            twin["sensor_age_seconds"] = None
    return {
        "sensor": state.latest,
        # decisions 列表头部即最新决策。
        "decision": state.decisions[0] if state.decisions else None,
        # 统计仍处于 pending 的 HITL 单数量。
        "pending_hitl": sum(x["status"] == "pending" for x in state.hitl),
        "agents": len(state.agent_cache),
        "digital_twin": twin,
        # 仅返回最近 8 条执行器 ACK。
        "recent_acks": state.actuator_acks[:8],
    }


@router.get("/api/audit")
def audit_list():
    """返回全部内存审计事件。"""
    return events()


@router.get("/api/audit/history")
def audit_history(limit: int = Query(100, ge=1, le=1000)):
    """返回最近的指定数量审计事件。"""
    # limit 由查询参数控制，范围 1～1000，默认 100；按时间倒序取尾部。
    return events()[-limit:]


@router.get("/api/config/thresholds")
def thresholds():
    """返回前端展示用的默认环境阈值。"""
    # 注意：这是展示用默认值，实际判定阈值以作物档案/各 Agent 内默认值为准。
    return {
        "temperature": {"min": 18, "max": 30},
        "humidity": {"min": 50, "max": 80},
        "ph": {"min": 5.5, "max": 7.5},
    }


@router.get("/api/health")
def health():
    """返回服务健康状态。"""
    return {"status": "ok", "version": "0.2.0"}
