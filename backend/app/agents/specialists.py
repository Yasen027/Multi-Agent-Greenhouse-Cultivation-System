from .base import BaseAgent
class RuleAgent(BaseAgent):
 def __init__(self,name): self.name=name
 async def run(self, context):
  r=context['reading']; findings=[]; rec=[]; risk='low'
  if self.name=='temperature' and r.temperature>30: findings=['temperature high']; rec=['ventilation_on']
  if self.name=='humidity' and r.humidity>80: findings=['humidity high']; rec=['ventilation_on']
  if self.name=='soil' and r.soil_moisture<30: findings=['soil dry']; rec=['irrigation_on']
  if self.name=='pest' and r.humidity>90: findings=['fungal risk']; risk='medium'
  return self.result(confidence=0.82,findings=findings,recommendations=rec,risk_level=risk)
