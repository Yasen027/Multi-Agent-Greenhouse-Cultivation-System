"""光照与二氧化碳分析 Agent。"""

from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class LightCO2Agent(BaseAgent):
    """光照与 CO2 控制专家。"""

    name = 'light_co2'
    prompt_name = 'light_co2'

    async def run(self, context: dict[str, Any]):
        r = context['reading']
        profile = context.get('crop_profile') or {}
        findings = []
        actions = []
        risk = 'low'
        confidence = 0.82

        # 读取作物光照与 CO2 阈值，缺失时使用默认值
        if isinstance(profile, dict):
            light_min = float(profile.get('light_min', 200))
            light_max = float(profile.get('light_max', 1200))
            co2_min = float(profile.get('co2_min', 350))
        else:
            light_min = 200
            light_max = 1200
            co2_min = 350

        # 光照不足：开启补光
        if r.light < light_min:
            findings.append('light low')
            actions.append('supplemental_light_on')

        # 光照过强且伴随高温：遮阴
        if r.light > light_max and r.temperature > float(profile.get('temperature_max', 30)):
            findings.append('excessive light with heat')
            actions.append('shade_on')
            risk = 'medium'

        # CO2 不足：提示补充
        if r.co2 < co2_min:
            findings.append('co2 low')
            actions.append('co2_enrichment_review')

        # 无异常时给出中性结论
        if not findings:
            findings.append('light and co2 within known thresholds')

        # 加载光照与 CO2 提示词
        crop = profile.get('crop', 'unknown') if isinstance(profile, dict) else 'unknown'
        stage = profile.get('stage', 'unknown') if isinstance(profile, dict) else 'unknown'
        prompt = prompt_loader.load('light_co2', {
            'crop': crop,
            'stage': stage,
            'sensor_data_json': r.model_dump(),
            'history_json': context.get('history', {}),
            'crop_profile_json': profile,
            'weather_json': context.get('weather', {}),
            'actuator_state': context.get('actuator_state', {}),
            'context': context.get('extra', {}),
        })

        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority='P2',
        )
