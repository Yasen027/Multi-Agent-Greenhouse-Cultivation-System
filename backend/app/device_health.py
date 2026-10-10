"""传感器与执行器的最小健康诊断、ACK 截止时间和熔断状态。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any, Iterable
from uuid import uuid4

from . import state
from .services import audit

# 参与健康诊断的传感器字段清单（与读数模型中的字段名对应）。
SENSOR_FIELDS = (
    "temperature",
    "humidity",
    "soil_moisture",
    "ph",
    "ec",
    "light",
    "co2",
)
SENSOR_NAMES = {
    "temperature": "温度",
    "humidity": "空气湿度",
    "soil_moisture": "土壤湿度",
    "ph": "pH",
    "ec": "EC",
    "light": "光照",
    "co2": "CO₂",
}


# 从环境变量读取整数阈值（下限 1）；缺失或解析失败时回落到默认值。
def _limit(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


# 统一时区：无时区信息的时间视为 UTC，保证时间差计算正确。
def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _iso(value: datetime | None = None) -> str:
    return _utc(value).isoformat()


# 容错解析 ISO 时间字符串：兼容 "Z" 后缀写法，解析失败返回 None。
def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


# 诊断问题集合发生变化时才写审计，避免每次轮询都产生审计噪音。
def _audit_changes(event: str, before: set[str], issues: dict[str, dict]) -> None:
    after = set(issues)
    if before != after:
        audit(event, {"issues": list(issues.values())})


# 重置全部健康状态：关闭待处理的设备故障审批，清空 ACK、熔断、卡死计数与问题列表。
def reset_health() -> None:
    for item in state.hitl:
        if item.get("type") == "device_failure" and item.get("status") == "pending":
            item["status"] = "resolved"
            audit("hitl_resolved", item)
    state.pending_acks.clear()
    state.acknowledged_commands.clear()
    state.actuator_failures.clear()
    state.actuator_circuits.clear()
    state.sensor_last_values.clear()
    state.sensor_repeat_counts.clear()
    state.sensor_issues.clear()
    state.actuator_issues.clear()
    state.sensor_monitor_started_at = _iso()
    state.digital_twin["last_sensor_at"] = None


# 记录一次传感器读数：先清除离线/越界问题，再逐字段统计连续不变次数，达到阈值判定卡死。
def record_sensor(reading: dict[str, Any], received_at: datetime | None = None) -> None:
    before = set(state.sensor_issues)
    threshold = _limit("SENSOR_STUCK_COUNT", 3)
    device_id = str(reading.get("device_id", "unknown"))
    previous = state.sensor_last_values.setdefault(device_id, {})
    repeats = state.sensor_repeat_counts.setdefault(device_id, {})

    state.sensor_issues.pop("sensor_offline", None)
    for key in list(state.sensor_issues):
        if key.startswith("out_of_range:"):
            state.sensor_issues.pop(key, None)
    for field in SENSOR_FIELDS:
        value = reading.get(field)
        # 与上次读数相同则重复计数 +1，一旦变化立即重置为 1。
        repeats[field] = (
            repeats.get(field, 0) + 1 if previous.get(field) == value else 1
        )
        previous[field] = value
        issue_key = "sensor_stuck:" + field
        if repeats[field] >= threshold:
            state.sensor_issues[issue_key] = {
                "code": "sensor_stuck",
                "sensor": field,
                "severity": "warning",
                "message": f"{SENSOR_NAMES[field]}连续 {threshold} 次未变化，疑似卡死",
                "detected_at": _iso(received_at),
            }
        else:
            state.sensor_issues.pop(issue_key, None)
    _audit_changes("sensor_diagnostic_changed", before, state.sensor_issues)


# 记录校验失败的读数：从错误位置取出字段名，标记为越界（critical）。
def record_invalid_sensor(errors: Iterable[dict[str, Any]]) -> None:
    before = set(state.sensor_issues)
    for error in errors:
        location = error.get("loc") or []
        field = str(location[-1]) if location else "unknown"
        key = "out_of_range:" + field
        state.sensor_issues[key] = {
            "code": "out_of_range",
            "sensor": field,
            "severity": "critical",
            "message": f"{SENSOR_NAMES.get(field, field)}读数超出合理范围",
            "detected_at": _iso(),
        }
    _audit_changes("sensor_diagnostic_changed", before, state.sensor_issues)


# 命令下发前处理：生成 command_id 并登记 ACK 截止时间；已熔断执行器的命令直接抑制。
def prepare_commands(
    commands: Iterable[dict[str, Any]], now: datetime | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prepared = []
    suppressed = []
    deadline = _utc(now) + timedelta(seconds=_limit("ACK_TIMEOUT_SECONDS", 5))
    for command in commands:
        payload = dict(command)
        actuator = str(payload.get("actuator", ""))
        # 执行器处于熔断状态时不再下发命令，该命令进入 suppressed 列表返回上层。
        if state.actuator_circuits.get(actuator):
            suppressed.append(payload)
            continue
        payload["command_id"] = str(payload.get("command_id") or uuid4())
        state.pending_acks[payload["command_id"]] = {
            **payload,
            "deadline": deadline.isoformat(),
        }
        prepared.append(payload)
    return prepared, suppressed


# 为熔断执行器创建设备故障人工审批；同一执行器已有待处理审批时不再重复创建。
def _open_failure_hitl(actuator: str, failures: int) -> None:
    if any(
        item.get("status") == "pending"
        and item.get("type") == "device_failure"
        and item.get("actuator") == actuator
        for item in state.hitl
    ):
        return
    item = {
        "id": str(uuid4()),
        "type": "device_failure",
        "actuator": actuator,
        "reason": f"{actuator} 连续 {failures} 次执行失败，已暂停自动重试",
        "status": "pending",
    }
    state.hitl.insert(0, item)
    audit("hitl_pending", item)


# 处理设备 ACK 回执：applied 清零失败计数并更新执行器状态；failed/timeout 累计失败，达到阈值熔断。
def record_ack(payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload.setdefault("timestamp", _iso())
    command_id = payload.get("command_id")
    if command_id:
        if command_id in state.acknowledged_commands:
            return
        state.acknowledged_commands[command_id] = payload["timestamp"]
        # ACK 历史只保留最近 200 条，防止内存无限增长。
        while len(state.acknowledged_commands) > 200:
            state.acknowledged_commands.pop(next(iter(state.acknowledged_commands)))
        state.pending_acks.pop(command_id, None)
    state.actuator_acks.insert(0, payload)
    del state.actuator_acks[100:]

    actuator = str(payload.get("actuator", ""))
    status = payload.get("status")
    # 成功回执更新状态并清零失败计数；失败/超时回执累计失败次数并进入熔断判定。
    if actuator and status == "applied":
        state.actuator_state[actuator] = payload.get("action")
        state.actuator_failures[actuator] = 0
        if not state.actuator_circuits.get(actuator):
            state.actuator_issues.pop("actuator_failure:" + actuator, None)
    elif actuator and status in {"failed", "timeout"}:
        failures = state.actuator_failures.get(actuator, 0) + 1
        state.actuator_failures[actuator] = failures
        threshold = _limit("ACTUATOR_FAILURE_LIMIT", 3)
        issue = {
            "code": "actuator_failure",
            "actuator": actuator,
            "severity": "warning",
            "message": f"{actuator} 连续执行失败 {failures} 次",
            "detected_at": _iso(),
        }
        if failures >= threshold:
            state.actuator_circuits[actuator] = True
            issue.update(
                code="circuit_open",
                severity="critical",
                message=f"{actuator} 连续失败 {failures} 次，已熔断并暂停重试",
            )
            _open_failure_hitl(actuator, failures)
        state.actuator_issues["actuator_failure:" + actuator] = issue
    audit("actuator_ack", payload)


# 周期健康检查：判定传感器离线（超过阈值秒数无有效数据），并把 ACK 超时的命令按失败回执处理。
def check_health(now: datetime | None = None) -> dict[str, Any]:
    current = _utc(now)
    before = set(state.sensor_issues)
    reference = _parse(
        state.digital_twin.get("last_sensor_at") or state.sensor_monitor_started_at
    )
    offline_after = _limit("SENSOR_OFFLINE_SECONDS", 6)
    # 设备在线但超过 offline_after 秒未收到有效传感器数据，即判定传感器离线。
    if (
        state.digital_twin.get("online")
        and reference
        and (current - reference).total_seconds() > offline_after
    ):
        state.sensor_issues["sensor_offline"] = {
            "code": "sensor_offline",
            "severity": "critical",
            "message": f"超过 {offline_after} 秒未收到有效传感器数据，设备离线",
            "detected_at": current.isoformat(),
        }
    _audit_changes("sensor_diagnostic_changed", before, state.sensor_issues)

    # 找出已超过 ACK 截止时间仍未回执的命令，统一按超时失败回执处理。
    expired = [
        (command_id, command)
        for command_id, command in list(state.pending_acks.items())
        if (_parse(command.get("deadline")) or current) <= current
    ]
    for command_id, command in expired:
        record_ack(
            {
                "command_id": command_id,
                "actuator": command.get("actuator"),
                "action": command.get("action"),
                "status": "timeout",
                "timestamp": current.isoformat(),
                "error": "ACK deadline exceeded",
            }
        )
    return health_snapshot()


# 人工审批通过后复位熔断：移除熔断标记与失败计数，允许该执行器再次下发命令。
def reset_actuator_circuit(actuator: str) -> None:
    state.actuator_circuits.pop(actuator, None)
    state.actuator_failures.pop(actuator, None)
    state.actuator_issues.pop("actuator_failure:" + actuator, None)
    audit("actuator_circuit_reset", {"actuator": actuator})


# 汇总传感器与执行器的健康快照，供 API 与决策服务引用。
def health_snapshot() -> dict[str, Any]:
    sensor_issues = list(state.sensor_issues.values())
    actuator_issues = list(state.actuator_issues.values())
    all_issues = sensor_issues + actuator_issues
    status = _issue_status(all_issues)
    return {
        "status": status,
        "sensor": {
            "status": _issue_status(sensor_issues),
            "issues": sensor_issues,
            "repeat_counts": state.sensor_repeat_counts,
            "offline_after_seconds": _limit("SENSOR_OFFLINE_SECONDS", 6),
        },
        "actuator": {
            "status": _issue_status(actuator_issues),
            "issues": actuator_issues,
            "consecutive_failures": dict(state.actuator_failures),
            "circuits": dict(state.actuator_circuits),
            "pending_ack_count": len(state.pending_acks),
            "ack_timeout_seconds": _limit("ACK_TIMEOUT_SECONDS", 5),
        },
    }


# 严重级别聚合：任一 critical 即整体 critical；否则有 warning 为 warning；全空为 healthy。
def _issue_status(issues: list[dict[str, Any]]) -> str:
    if any(issue["severity"] == "critical" for issue in issues):
        return "critical"
    return "warning" if issues else "healthy"


__all__ = [
    "check_health",
    "health_snapshot",
    "prepare_commands",
    "record_ack",
    "record_invalid_sensor",
    "record_sensor",
    "reset_actuator_circuit",
    "reset_health",
]
