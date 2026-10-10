"""审计与安全检查服务。"""

from datetime import datetime

from .action_registry import validate_commands

# 内存中的审计事件列表
_events = []
# 尽力初始化 SQLite 审计；失败则降级为仅内存审计（save_audit 置 None）。
try:
    from .db.session import init_db, save_audit

    init_db()
except Exception:
    save_audit = None


def audit(event, payload):
    """记录一条审计事件。"""
    item = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "payload": payload,
    }
    # 先写内存审计，再尽力写 SQLite；数据库异常被吞掉，不影响业务主流程。
    _events.append(item)
    if save_audit:
        try:
            save_audit(event, payload)
        except Exception:
            pass


def events():
    """返回全部内存审计事件。"""
    return _events


def safety(reading, commands):
    """对读数与指令做安全检查，返回 (状态, 原因列表)。"""
    reasons = []
    # 极端温度
    if reading.temperature > 40:
        reasons.append("温度超过 40℃，达到极端高温安全阈值")
    # 异常 pH
    if reading.ph < 4 or reading.ph > 8:
        reasons.append("pH 超出 4～8 的安全范围")
    # 化学农药
    if any(c.get("actuator") == "pesticide" for c in commands):
        reasons.append("控制命令涉及化学农药")
    # 校验动作注册表、执行器白名单和设备互斥规则。
    reasons.extend(validate_commands(commands))
    # 存在任何原因即升级为人工介入（need_hitl），否则放行。
    return ("need_hitl", reasons) if reasons else ("allow", [])
