from ..prompt_loader import prompt_loader
from ..schemas import ActuatorCommand


class DecisionFusionAgent:
 def fuse(self, outputs, context=None):
  context = context or {}
  profile = context.get('crop_profile') or {}
  mapping = {
   'ventilation_on': ('ventilation', 'on'), 'ventilation_off': ('ventilation', 'off'),
   'irrigation_on': ('irrigation', 'on'), 'irrigation_off': ('irrigation', 'off'),
   'heating_on': ('heating', 'on'), 'heating_off': ('heating', 'off'),
   'mist_on': ('mister', 'on'), 'supplemental_light_on': ('grow_light', 'on'),
   'shade_on': ('shade', 'on'), 'co2_on': ('co2', 'on'),
   'fan_on': ('fan', 'on'), 'fan_off': ('fan', 'off'),
  }
  commands=[]; seen=set()
  for agent in outputs or []:
   for rec in agent.get('recommendations',[]) or []:
    if rec not in mapping: continue
    actuator, action = mapping[rec]
    key=(actuator, action)
    if key in seen: continue
    seen.add(key)
    command = ActuatorCommand(actuator=actuator, action=action, reason=agent.get('agent','agent'))
    commands.append(command.model_dump() if hasattr(command, 'model_dump') else command.dict())
  self.last_prompt = prompt_loader.load('decision_fusion', {
   'crop': context.get('crop', profile.get('crop', 'unknown')), 'stage': context.get('stage', profile.get('stage', 'unknown')),
   'crop_profile_json': profile, 'agents_json': outputs or [], 'actuator_state': context.get('actuator_state',{}),
   'safety_rules': context.get('safety_rules',{}),
  })
  return commands
decision_agent=DecisionFusionAgent()
