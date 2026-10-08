from datetime import datetime
from .action_registry import validate_commands
_events=[]
try:
 from .db.session import init_db,save_audit
 init_db()
except Exception: save_audit=None
def audit(event,payload):
 item={'timestamp':datetime.utcnow().isoformat(),'event':event,'payload':payload}; _events.append(item)
 if save_audit:
  try: save_audit(event,payload)
  except Exception: pass
def events(): return _events
def safety(reading, commands):
 reasons=[]
 if reading.temperature>40: reasons.append('extreme temperature')
 if reading.ph<4 or reading.ph>8: reasons.append('unsafe pH')
 if any(c.get('actuator')=='pesticide' for c in commands): reasons.append('chemical pesticide')
 reasons.extend(validate_commands(commands))
 return ('need_hitl',reasons) if reasons else ('allow',[])
