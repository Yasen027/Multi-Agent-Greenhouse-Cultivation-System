"""Agent 注册与构建。

根据名称列表构建对应的专家 Agent 实例，
为编排器提供可并发执行的分析单元。
"""

from .crop_stage_agent import CropStageAgent
from .humidity_agent import HumidityAgent
from .irrigation_agent import IrrigationAgent
from .light_co2_agent import LightCO2Agent
from .soil_agent import SoilAgent
from .specialists import RuleAgent
from .temperature_agent import TemperatureAgent

# 支持的 Agent 名称列表
AGENT_NAMES = [
    'soil',
    'temperature',
    'humidity',
    'pest',
    'irrigation',
    'light_co2',
    'crop_stage',
    'crop_identification',
]


def build_agents():
    """按名称构建 Agent 实例列表（跳过由触发器驱动的作物识别）。"""
    # 名称到构造器的映射，未匹配的名称回退到通用规则 Agent
    factories = {
        'soil': SoilAgent,
        'temperature': TemperatureAgent,
        'humidity': HumidityAgent,
        'irrigation': IrrigationAgent,
        'light_co2': LightCO2Agent,
        'crop_stage': CropStageAgent,
    }
    agents = []
    for name in AGENT_NAMES:
        # 作物识别由单独触发器驱动，不纳入常规循环
        if name == 'crop_identification':
            continue
        factory = factories.get(name)
        if factory is not None:
            agents.append(factory())
        else:
            agents.append(RuleAgent(name))
    return agents
