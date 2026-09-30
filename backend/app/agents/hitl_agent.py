class SafetyHITLAgent:
 def evaluate(self, reading, commands):
  reasons=[]
  if reading.temperature>40: reasons.append('extreme temperature')
  if reading.ph<4 or reading.ph>8: reasons.append('unsafe pH')
  if any(c.get('actuator')=='pesticide' for c in commands): reasons.append('chemical pesticide')
  return {'status':'need_hitl' if reasons else 'allow','reasons':reasons}
hitl_agent=SafetyHITLAgent()
