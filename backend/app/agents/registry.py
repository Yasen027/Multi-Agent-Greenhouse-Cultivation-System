# Agent 注册表：集中声明系统全部 Agent 名称并构建其实例列表。
from .crop_stage_agent import CropStageAgent
from .humidity_agent import HumidityAgent
from .irrigation_agent import IrrigationAgent
from .light_co2_agent import LightCO2Agent
from .soil_agent import SoilAgent
from .specialists import RuleAgent
from .temperature_agent import TemperatureAgent

# 全部 Agent 的逻辑名称；Orchestrator 按此列表逐个构建并并行执行。
AGENT_NAMES = [
    "soil",
    "temperature",
    "humidity",
    "pest",
    "irrigation",
    "light_co2",
    "crop_stage",
    "crop_identification",
]


def build_agents():
    # 按名称构建 Agent 实例：有专属实现的直接实例化，
    # 未实现的（pest 等）用通用 RuleAgent 兜底；crop_identification 不参与常规轮询。
    return [
        (
            SoilAgent()
            if n == "soil"
            else (
                TemperatureAgent()
                if n == "temperature"
                else (
                    HumidityAgent()
                    if n == "humidity"
                    else (
                        IrrigationAgent()
                        if n == "irrigation"
                        else (
                            LightCO2Agent()
                            if n == "light_co2"
                            else CropStageAgent() if n == "crop_stage" else RuleAgent(n)
                        )
                    )
                )
            )
        )
        for n in AGENT_NAMES
        if n != "crop_identification"
    ]
