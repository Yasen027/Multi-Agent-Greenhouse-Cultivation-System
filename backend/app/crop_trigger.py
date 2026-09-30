from datetime import datetime, timedelta

class CropTriggerManager:
 def __init__(self, interval_hours=168):
  self.interval_hours=interval_hours; self.last_run=None; self.reason='startup'; self.current_crop=None; self.season=1
 def due(self): return self.last_run is None or datetime.utcnow()-self.last_run>=timedelta(hours=self.interval_hours)
 def should_run(self, reason=None, force=False, mismatch=False): return force or mismatch or reason in ('startup','new_season','crop_change') or self.due()
 def mark(self, reason): self.last_run=datetime.utcnow(); self.reason=reason
 def status(self): return {'last_run': self.last_run.isoformat() if self.last_run else None,'interval_hours':self.interval_hours,'current_crop':self.current_crop,'season':self.season,'last_reason':self.reason,'due':self.due()}
manager=CropTriggerManager()
