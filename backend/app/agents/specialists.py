# 通用规则型 Agent：为尚无专属实现的领域（如 pest）提供简单的阈值兜底判断。
from .base import BaseAgent


class RuleAgent(BaseAgent):
    # 按传入名称区分领域，共用同一套 if 规则分支。
    def __init__(self, name):
        self.name = name

    async def run(self, context):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        rec = []
        risk = "low"
        # 温度超过档案上限（默认 30℃）时给出通风建议。
        if self.name == "temperature" and r.temperature > float(
            profile.get("temperature_max", 30)
        ):
            findings = ["temperature high"]
            rec = ["ventilation_on"]
        if self.name == "humidity" and r.humidity > float(
            profile.get("humidity_max", 80)
        ):
            # 湿度超过档案上限（默认 80%）时给出通风建议。
            findings = ["humidity high"]
            rec = ["ventilation_on"]
        # 土壤湿度低于档案下限（默认 30%）时给出灌溉建议。
        if self.name == "soil" and r.soil_moisture < float(
            profile.get("soil_moisture_min", 30)
        ):
            findings = ["soil dry"]
            rec = ["irrigation_on"]
        # pest 规则：湿度超过 90% 时提示真菌病害风险（注意此处默认值与其他分支不同）。
        if self.name == "pest" and r.humidity > float(profile.get("humidity_max", 90)):
            findings = ["fungal risk"]
            risk = "medium"
        return self.result(
            confidence=0.82, findings=findings, recommendations=rec, risk_level=risk
        )
