from ..prompt_loader import prompt_loader
class DecisionFusionAgent:
 def fuse(self, outputs, context=None):
  commands=[]
  for a in outputs:
   for rec in a.get('recommendations',[]):
    if rec=='ventilation_on': commands.append({'actuator':'ventilation','action':'on','reason':a['agent']})
    if rec=='irrigation_on': commands.append({'actuator':'irrigation','action':'on','reason':a['agent']})
    if rec=='heating_on': commands.append({'actuator':'heating','action':'on','reason':a['agent']})
  self.last_prompt=prompt_loader.load('decision_fusion',{'crop':(context or {}).get('crop','unknown'),'stage':(context or {}).get('stage','unknown'),'agents_json':outputs,'actuator_state':(context or {}).get('actuator_state',{}),'safety_rules':(context or {}).get('safety_rules',{})})
  return commands
decision_agent=DecisionFusionAgent()
