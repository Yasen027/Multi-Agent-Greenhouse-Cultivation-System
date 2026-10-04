from typing import Any
from ..prompt_loader import prompt_loader
from .base import BaseAgent
class SoilAgent(BaseAgent):
 name='soil'; prompt_name='soil'
 async def run(self, context: dict[str,Any]):
  r=context['reading']; profile=context.get('crop_profile') or {}; ph=r.ph; findings=[]; actions=[]; risk='low'; confidence=0.82
  target_ph=float(profile.get('ph',6.2)) if isinstance(profile,dict) else 6.2
  target_ec=float(profile.get('ec',2.0)) if isinstance(profile,dict) else 2.0
  delta=abs(ph-target_ph)
  if ph<4.5 or ph>8.5: findings.append('pH critical'); risk='critical'; confidence=.65; actions.append('human_review_soil')
  elif delta>=.8: findings.append('pH severely deviated'); risk='high'; actions.append('adjust_ph')
  elif delta>=.3: findings.append('pH warning'); risk='medium'; actions.append('adjust_ph')
  if r.ec>target_ec*2: findings.append('EC critical'); risk='critical'; actions.append('human_review_soil'); confidence=.65
  elif r.ec>target_ec*1.3: findings.append('EC high'); risk='medium'; actions.append('drainage_check')
  moisture_min=float(profile.get('soil_moisture_min',30)) if isinstance(profile,dict) else 30
  moisture_max=float(profile.get('soil_moisture_max',70)) if isinstance(profile,dict) else 70
  if r.soil_moisture<moisture_min: findings.append('soil moisture low'); actions.append('irrigation_on')
  elif r.soil_moisture>moisture_max: findings.append('soil moisture high'); actions.append('irrigation_off'); risk='medium'
  if not findings: findings.append('soil within known thresholds')
  prompt=prompt_loader.load('soil',{'stage':profile.get('stage','unknown') if isinstance(profile,dict) else 'unknown','crop':profile.get('crop','unknown') if isinstance(profile,dict) else 'unknown','crop_profile_json':profile,'sensor_data_json':r.model_dump(),'history_json':context.get('history',{}),'weather_json':context.get('weather',{}),'context':context.get('extra',{})})
  return self.result(confidence=confidence,findings=findings,recommendations=actions,risk_level=risk,prompt_loaded=bool(prompt))
