from ..prompt_loader import prompt_loader
from ..schemas import ActuatorCommand
from ..action_registry import action_alert, get_action


class DecisionFusionAgent:
 def fuse(self, outputs, context=None):
  context = context or {}
  profile = context.get('crop_profile') or {}
  self.last_alerts = []
  self.last_hitl_actions = []
  commands=[]; seen=set()
  for agent in outputs or []:
   for rec in agent.get('recommendations',[]) or []:
    spec = get_action(rec)
    if spec is None:
     self.last_alerts.append(action_alert(rec, agent.get('agent','agent')))
     self.last_hitl_actions.append(rec)
     continue
    if spec.kind != 'command' and not spec.actuator:
     alert = action_alert(rec, agent.get('agent','agent'))
     self.last_alerts.append(alert)
     if spec.requires_hitl: self.last_hitl_actions.append(rec)
     continue
    actuator, action = spec.actuator, spec.action
    key=(actuator, action)
    if key in seen: continue
    seen.add(key)
    command = ActuatorCommand(actuator=actuator, action=action, reason=agent.get('agent','agent'))
    command_data = command.model_dump() if hasattr(command, 'model_dump') else command.dict()
    commands.append(command_data)
    if spec.requires_hitl:
     self.last_hitl_actions.append(rec)
     self.last_alerts.append(action_alert(rec, agent.get('agent','agent')))
  self.last_prompt = prompt_loader.load('decision_fusion', {
   'crop': context.get('crop', profile.get('crop', 'unknown')), 'stage': context.get('stage', profile.get('stage', 'unknown')),
   'crop_profile_json': profile, 'agents_json': outputs or [], 'actuator_state': context.get('actuator_state',{}),
   'safety_rules': context.get('safety_rules',{}),
  })
  return commands
decision_agent=DecisionFusionAgent()
