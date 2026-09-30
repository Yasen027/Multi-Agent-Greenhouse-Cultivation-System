from typing import Any, Optional
from .prompt_loader import prompt_loader

CROP_HINTS = {'tomato': ('tomato','番茄','西红柿'),'lettuce': ('lettuce','生菜'),'strawberry': ('strawberry','草莓'),'cucumber': ('cucumber','黄瓜'),'pepper': ('pepper','辣椒')}

def build_prompt(context: dict[str, Any]) -> str:
 return prompt_loader.load('crop_identification', context)

def identify_crop(image_url: Optional[str]=None, metadata: Optional[dict[str,Any]]=None, user_input: str='') -> dict[str,Any]:
 text=' '.join([str(image_url or ''), str(metadata or {}), user_input]).lower()
 for crop,hints in CROP_HINTS.items():
  if any(h in text for h in hints): return {'crop':crop,'crop_species':crop,'crop_variety':None,'crop_profile_key':crop,'confidence':0.92,'method':'filename_or_metadata','evidence':text,'human_intervention':{'required':False,'urgency':'none','reason':'','question_to_human':''}}
 return {'crop':'unknown','crop_species':'unknown','crop_variety':None,'crop_profile_key':None,'confidence':0.2,'method':'fallback','evidence':text,'human_intervention':{'required':True,'urgency':'medium','reason':'无法从输入确定作物或知识库档案','question_to_human':'请确认当前温室种植的作物和品种。'}}

async def evaluate(reading) -> dict[str,Any]:
 result=identify_crop(getattr(reading,'image_url',None),{'device_id':getattr(reading,'device_id','')})
 return {'agent':'crop_identification','status':'ok','confidence':result['confidence'],'findings':result,'recommendations':['set_crop_profile'] if result['crop']!='unknown' else ['request_human_confirmation'],'recommended_actions':['设置当前作物档案'],'risk_level':'low' if result['confidence']>=0.7 else 'medium','crop':result['crop'],'method':result['method'],'human_intervention':result['human_intervention']}
