from .specialists import RuleAgent
from .soil_agent import SoilAgent
from .temperature_agent import TemperatureAgent
from .humidity_agent import HumidityAgent
from .irrigation_agent import IrrigationAgent
from .light_co2_agent import LightCO2Agent
from .crop_stage_agent import CropStageAgent
from .humidity_agent import HumidityAgent
AGENT_NAMES=['soil','temperature','humidity','pest','irrigation','light_co2','crop_stage','crop_identification']
def build_agents():
 return [SoilAgent() if n=='soil' else TemperatureAgent() if n=='temperature' else HumidityAgent() if n=='humidity' else IrrigationAgent() if n=='irrigation' else LightCO2Agent() if n=='light_co2' else CropStageAgent() if n=='crop_stage' else RuleAgent(n) for n in AGENT_NAMES if n!='crop_identification']
