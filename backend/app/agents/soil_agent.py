from typing import Any
from ..prompt_loader import prompt_loader
from .base import BaseAgent
class SoilAgent(BaseAgent):
 name='soil'; prompt_name='soil'
 async def run(self, context: dict[str,Any]):
  r=context['reading']; profile=context.get('crop_profile') or {}; ph=r.ph; findings=[]; actions=[]; risk='low'; confidence=0.82
  target_ph=float(profile.get('ph',6.2)) if isinstance(profile,dict) else 6.2
  delta=abs(ph-target_ph)
  if ph<4.5 or ph>8.5: findings.append('pH critical'); risk='critical'; confidence=.65; actions.append('human_review_soil')
  elif delta>=.8: findings.append('pH severely deviated'); risk='high'; actions.append('adjust_ph')
  elif delta>=.3: findings.append('pH warning'); risk='medium'; actions.append('adjust_ph')
  if r.soil_moisture<30: findings.append('soil moisture low'); actions.append('irrigation_on')
  if not findings: findings.append('soil within known thresholds')
  prompt=prompt_loader.load('soil',{'stage':profile.get('stage','unknown') if isinstance(profile,dict) else 'unknown','crop':profile.get('crop','unknown') if isinstance(profile,dict) else 'unknown','crop_profile_json':profile,'sensor_data_json':r.model_dump(),'history_json':context.get('history',{}),'weather_json':context.get('weather',{}),'context':context.get('extra',{})})
  return self.result(confidence=confidence,findings=findings,recommendations=actions,risk_level=risk,prompt_loaded=bool(prompt))
