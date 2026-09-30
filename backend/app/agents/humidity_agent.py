from typing import Any
from ..prompt_loader import prompt_loader
from .base import BaseAgent
class HumidityAgent(BaseAgent):
 name='humidity'; prompt_name='humidity'
 async def run(self, context: dict[str,Any]):
  r=context['reading']; profile=context.get('crop_profile') or {}; findings=[]; actions=[]; risk='low'; confidence=.82
  target_min=float(profile.get('humidity_min',50)) if isinstance(profile,dict) else 50
  target_max=float(profile.get('humidity_max',80)) if isinstance(profile,dict) else 80
  if r.humidity>95: findings.append('humidity critical and disease risk'); risk='high'; actions.extend(['ventilation_on','notify_pest_agent']); confidence=.68
  elif r.humidity>target_max: findings.append('humidity high'); risk='medium'; actions.append('ventilation_on')
  elif r.humidity<target_min: findings.append('humidity low'); actions.append('mist_on')
  if not findings: findings.append('humidity within known thresholds')
  prompt=prompt_loader.load('humidity',{'stage':profile.get('stage','unknown') if isinstance(profile,dict) else 'unknown','crop':profile.get('crop','unknown') if isinstance(profile,dict) else 'unknown','crop_profile_json':profile,'sensor_data_json':r.model_dump(),'history_json':context.get('history',{}),'weather_json':context.get('weather',{}),'actuator_state':context.get('actuator_state',{}),'context':context.get('extra',{})})
  return self.result(confidence=confidence,findings=findings,recommendations=actions,risk_level=risk,prompt_loaded=bool(prompt),priority='P1' if risk in ('high','emergency') else 'P2',vpd=None,condensation_risk=r.humidity>90)
