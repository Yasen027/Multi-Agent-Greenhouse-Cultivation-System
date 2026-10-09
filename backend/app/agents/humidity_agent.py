"""湿度分析 Agent。

依据作物湿度阈值评估空气湿度是否偏离目标区间，
并给出通风/加湿等建议。
"""

from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class HumidityAgent(BaseAgent):
    """空气湿度控制专家。"""

    name = 'humidity'
    prompt_name = 'humidity'

    async def run(self, context: dict[str, Any]):
        r = context['reading']
        profile = context.get('crop_profile') or {}
        findings = []
        actions = []
        risk = 'low'
        confidence = 0.82

        # 读取作物湿度阈值，缺失时使用默认值
        if isinstance(profile, dict):
            target_min = float(profile.get('humidity_min', 50))
            target_max = float(profile.get('humidity_max', 80))
        else:
            target_min = 50
            target_max = 80

        # 分档判断湿度偏离程度
        if r.humidity > 95:
            findings.append('humidity critical and disease risk')
            risk = 'high'
            actions.extend(['ventilation_on', 'notify_pest_agent'])
            confidence = 0.68
        elif r.humidity > target_max:
            findings.append('humidity high')
            risk = 'medium'
            actions.append('ventilation_on')
        elif r.humidity < target_min:
            findings.append('humidity low')
            actions.append('mist_on')

        if not findings:
            findings.append('humidity within known thresholds')

        # 加载湿度提示词
        stage = profile.get('stage', 'unknown') if isinstance(profile, dict) else 'unknown'
        crop = profile.get('crop', 'unknown') if isinstance(profile, dict) else 'unknown'
        prompt = prompt_loader.load('humidity', {
            'stage': stage,
            'crop': crop,
            'crop_profile_json': profile,
            'sensor_data_json': r.model_dump(),
            'history_json': context.get('history', {}),
            'weather_json': context.get('weather', {}),
            'actuator_state': context.get('actuator_state', {}),
            'context': context.get('extra', {}),
        })

        priority = 'P1' if risk in ('high', 'emergency') else 'P2'
        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority=priority,
            vpd=None,
            condensation_risk=r.humidity > 90,
        )
