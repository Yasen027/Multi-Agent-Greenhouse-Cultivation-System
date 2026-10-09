"""Agent 编排器。

将传感器读数分发给所有领域 Agent 并发执行，
合并分析结果，供决策融合阶段使用。
"""

import asyncio
from typing import Any, Dict

from .. import state
from ..crop_identification_agent import evaluate as crop_identification
from ..prompt_loader import prompt_loader
from .registry import build_agents


def _dump(reading: Any) -> Dict[str, Any]:
    """将 Pydantic 读数对象转换为字典。"""
    return reading.model_dump() if hasattr(reading, 'model_dump') else reading.dict()


class Orchestrator:
    """负责编排各领域 Agent 并发运行。"""

    async def run(self, reading, crop_profile=None, history=None, weather=None, actuator_state=None):
        # 作物档案为空时视为空字典
        profile = crop_profile if isinstance(crop_profile, dict) else {}

        # 构造传给各 Agent 的统一上下文
        context = {
            'reading': reading,
            'crop_profile': profile,
            'sensor_data': _dump(reading),
            'history': history if history is not None else state.history,
            'weather': weather if weather is not None else state.weather,
            'actuator_state': actuator_state if actuator_state is not None else state.actuator_state,
            'extra': {},
        }

        agents = build_agents()

        # 组装编排提示词变量
        variables = {
            'crop': profile.get('crop', 'unknown'),
            'stage': profile.get('stage', 'unknown'),
            'sensor_data_json': context['sensor_data'],
            'history_json': context['history'],
            'weather_json': context['weather'],
            'actuator_state': context['actuator_state'],
            'crop_profile_json': profile,
            'agents_json': [a.name for a in agents],
            'safety_rules': {'temperature_max': 40, 'temperature_min': 5, 'ph_min': 4, 'ph_max': 8},
        }
        self.last_prompt = prompt_loader.load('orchestrator', variables)

        # 并发执行所有领域 Agent
        results = list(await asyncio.gather(*(a.run(context) for a in agents)))

        # 作物识别由触发器驱动；档案已生效时避免每个周期重复的低置信度检查
        if not profile.get('crop') and getattr(reading, 'image_url', None):
            results.append(await crop_identification(reading))
        return results


# 全局编排器单例
orchestrator = Orchestrator()


async def run_all(reading, crop_profile=None, history=None, weather=None, actuator_state=None):
    """供外部调用的编排入口。"""
    return await orchestrator.run(reading, crop_profile, history, weather, actuator_state)
