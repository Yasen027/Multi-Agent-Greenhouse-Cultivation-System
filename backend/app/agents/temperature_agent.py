"""温度分析 Agent。

依据作物温度阈值评估温室温度是否偏离目标区间，
并给出加热/通风建议。
"""

from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class TemperatureAgent(BaseAgent):
    """温度控制专家。"""

    name = 'temperature'
    prompt_name = 'temperature'

    async def run(self, context: dict[str, Any]):
        r = context['reading']
        profile = context.get('crop_profile') or {}
        findings = []
        actions = []
        risk = 'low'
        confidence = 0.82

        # 读取作物温度阈值，缺失时使用默认值
        if isinstance(profile, dict):
            target_min = float(profile.get('temperature_min', 18))
            target_max = float(profile.get('temperature_max', 30))
        else:
            target_min = 18
            target_max = 30

        # 分档判断温度偏离程度
        if r.temperature > 40 or r.temperature < 5:
            findings.append('temperature emergency')
            risk = 'emergency'
            confidence = 0.65
            actions.append('human_review_temperature')
        elif r.temperature < target_min - 8 or r.temperature > target_max + 8:
            findings.append('temperature severely deviated')
            risk = 'high'
            actions.append('heating_on' if r.temperature < target_min else 'ventilation_on')
        elif r.temperature < target_min - 3 or r.temperature > target_max + 3:
            findings.append('temperature warning')
            risk = 'medium'
            actions.append('heating_on' if r.temperature < target_min else 'ventilation_on')
        elif r.temperature < target_min:
            actions.append('heating_on')
        elif r.temperature > target_max:
            actions.append('ventilation_on')

        if not findings:
            findings.append('temperature within known thresholds')

        # 加载温度提示词
        stage = profile.get('stage', 'unknown') if isinstance(profile, dict) else 'unknown'
        crop = profile.get('crop', 'unknown') if isinstance(profile, dict) else 'unknown'
        prompt = prompt_loader.load('temperature', {
            'stage': stage,
            'crop': crop,
            'crop_profile_json': profile,
            'sensor_data_json': r.model_dump(),
            'history_json': context.get('history', {}),
            'weather_json': context.get('weather', {}),
            'actuator_state': context.get('actuator_state', {}),
            'context': context.get('extra', {}),
        })

        priority = 'P0' if risk == 'emergency' else 'P2'
        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority=priority,
        )
