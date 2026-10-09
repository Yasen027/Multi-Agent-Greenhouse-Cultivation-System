"""灌溉分析 Agent。

依据作物土壤湿度阈值判断是否需要灌溉或排水。
"""

from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class IrrigationAgent(BaseAgent):
    """土壤水分与灌溉控制专家。"""

    name = 'irrigation'
    prompt_name = 'irrigation'

    async def run(self, context: dict[str, Any]):
        r = context['reading']
        profile = context.get('crop_profile') or {}
        findings = []
        actions = []
        risk = 'low'
        confidence = 0.82

        # 读取作物土壤湿度阈值，缺失时使用默认值
        if isinstance(profile, dict):
            low = float(profile.get('soil_moisture_min', 30))
            high = float(profile.get('soil_moisture_max', 70))
        else:
            low = 30
            high = 70

        # 土壤过干：开启灌溉；过湿：停止灌溉并检查排水
        if r.soil_moisture < low:
            findings.append('soil moisture below target')
            actions.append('irrigation_on')
        elif r.soil_moisture > high:
            findings.append('soil saturation risk')
            actions.extend(['irrigation_off', 'drainage_check'])
            risk = 'medium'

        # 阀门故障：需要人工复核
        if context.get('actuator_state', {}).get('valve_fault'):
            findings.append('valve fault')
            actions.append('human_review_irrigation')
            risk = 'high'
            confidence = 0.65

        # 无异常时给出中性结论
        if not findings:
            findings.append('soil moisture within known thresholds')

        # 加载灌溉提示词
        crop = profile.get('crop', 'unknown') if isinstance(profile, dict) else 'unknown'
        stage = profile.get('stage', 'unknown') if isinstance(profile, dict) else 'unknown'
        prompt = prompt_loader.load('irrigation', {
            'crop': crop,
            'stage': stage,
            'sensor_data_json': r.model_dump(),
            'history_json': context.get('history', {}),
            'crop_profile_json': profile,
            'weather_json': context.get('weather', {}),
            'actuator_state': context.get('actuator_state', {}),
            'context': context.get('extra', {}),
        })

        priority = 'P1' if risk == 'high' else 'P2'
        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority=priority,
        )
