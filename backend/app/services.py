"""审计与安全检查服务。"""

from datetime import datetime
<<<<<<< Updated upstream
_events=[]
=======

from .action_registry import validate_commands

# 内存中的审计事件列表
_events = []

>>>>>>> Stashed changes
try:
    from .db.session import init_db, save_audit
    init_db()
except Exception:
    # 数据库不可用时降级为纯内存审计
    save_audit = None


def audit(event, payload):
    """记录一条审计事件。"""
    item = {
        'timestamp': datetime.utcnow().isoformat(),
        'event': event,
        'payload': payload,
    }
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
<<<<<<< Updated upstream
 reasons=[]
 if reading.temperature>40: reasons.append('extreme temperature')
 if reading.ph<4 or reading.ph>8: reasons.append('unsafe pH')
 if any(c.get('actuator')=='pesticide' for c in commands): reasons.append('chemical pesticide')
 return ('need_hitl',reasons) if reasons else ('allow',[])
=======
    """对读数与指令做安全检查，返回 (状态, 原因列表)。"""
    reasons = []
    # 极端温度
    if reading.temperature > 40:
        reasons.append('extreme temperature')
    # 异常 pH
    if reading.ph < 4 or reading.ph > 8:
        reasons.append('unsafe pH')
    # 化学农药
    if any(c.get('actuator') == 'pesticide' for c in commands):
        reasons.append('chemical pesticide')
    reasons.extend(validate_commands(commands))
    if reasons:
        return ('need_hitl', reasons)
    return ('allow', [])
>>>>>>> Stashed changes
