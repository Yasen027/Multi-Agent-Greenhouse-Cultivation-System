from .base import BaseAgent


class RuleAgent(BaseAgent):
    def __init__(self, name):
        self.name = name

    async def run(self, context):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        rec = []
        risk = "low"
        if self.name == "temperature" and r.temperature > float(
            profile.get("temperature_max", 30)
        ):
            findings = ["temperature high"]
            rec = ["ventilation_on"]
        if self.name == "humidity" and r.humidity > float(
            profile.get("humidity_max", 80)
        ):
            findings = ["humidity high"]
            rec = ["ventilation_on"]
        if self.name == "soil" and r.soil_moisture < float(
            profile.get("soil_moisture_min", 30)
        ):
            findings = ["soil dry"]
            rec = ["irrigation_on"]
        if self.name == "pest" and r.humidity > float(profile.get("humidity_max", 90)):
            findings = ["fungal risk"]
            risk = "medium"
        return self.result(
            confidence=0.82, findings=findings, recommendations=rec, risk_level=risk
        )
