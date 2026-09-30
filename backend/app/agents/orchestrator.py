import asyncio
from .registry import build_agents
from ..crop_identification_agent import evaluate as crop_identification
class Orchestrator:
 async def run(self, reading, crop_profile=None):
  context={'reading':reading,'crop_profile':crop_profile,'history':{},'weather':{},'actuator_state':{},'extra':{}}
  self.last_prompt = __import__('backend.app.prompt_loader', fromlist=['prompt_loader']).prompt_loader.load('orchestrator', {'crop':(crop_profile or {}).get('crop','unknown') if isinstance(crop_profile,dict) else 'unknown','stage':(crop_profile or {}).get('stage','unknown') if isinstance(crop_profile,dict) else 'unknown','sensor_data_json':reading.model_dump(),'history_json':{},'actuator_state':{},'agents_json':[],'safety_rules':{}})
  results=list(await asyncio.gather(*(a.run(context) for a in build_agents())))
  results.append(await crop_identification(reading))
  return results
orchestrator=Orchestrator()
async def run_all(reading, crop_profile=None): return await orchestrator.run(reading,crop_profile)
