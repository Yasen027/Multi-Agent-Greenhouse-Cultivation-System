"""通用规则 Agent。

用于没有独立实现的领域（如 pest），
基于简单阈值规则给出基础建议。
"""

from .base import BaseAgent


class RuleAgent(BaseAgent):
    """基于阈值规则的通用 Agent。"""

    def __init__(self, name):
        self.name = name

    async def run(self, context):
        r = context['reading']
        profile = context.get('crop_profile') or {}
        findings = []
        rec = []
        risk = 'low'

        # 温度过高：建议通风
        if self.name == 'temperature' and r.temperature > float(profile.get('temperature_max', 30)):
            findings = ['temperature high']
            rec = ['ventilation_on']

        # 湿度过高：建议通风
        if self.name == 'humidity' and r.humidity > float(profile.get('humidity_max', 80)):
            findings = ['humidity high']
            rec = ['ventilation_on']

        # 土壤过干：建议灌溉
        if self.name == 'soil' and r.soil_moisture < float(profile.get('soil_moisture_min', 30)):
            findings = ['soil dry']
            rec = ['irrigation_on']

        # 高湿引发真菌风险
        if self.name == 'pest' and r.humidity > float(profile.get('humidity_max', 90)):
            findings = ['fungal risk']
            risk = 'medium'

        return self.result(
            confidence=0.82,
            findings=findings,
            recommendations=rec,
            risk_level=risk,
        )
