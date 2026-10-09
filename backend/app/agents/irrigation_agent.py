from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class IrrigationAgent(BaseAgent):
    name = "irrigation"
    prompt_name = "irrigation"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        low = (
            float(profile.get("soil_moisture_min", 30))
            if isinstance(profile, dict)
            else 30
        )
        high = (
            float(profile.get("soil_moisture_max", 70))
            if isinstance(profile, dict)
            else 70
        )
        if r.soil_moisture < low:
            findings.append("soil moisture below target")
            actions.append("irrigation_on")
        elif r.soil_moisture > high:
            findings.append("soil saturation risk")
            actions.extend(["irrigation_off", "drainage_check"])
            risk = "medium"
        if context.get("actuator_state", {}).get("valve_fault"):
            findings.append("valve fault")
            actions.append("human_review_irrigation")
            risk = "high"
            confidence = 0.65
        prompt = prompt_loader.load(
            "irrigation",
            {
                "crop": (
                    profile.get("crop", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "stage": (
                    profile.get("stage", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "sensor_data_json": r.model_dump(),
                "history_json": context.get("history", {}),
                "crop_profile_json": profile,
                "weather_json": context.get("weather", {}),
                "actuator_state": context.get("actuator_state", {}),
                "context": context.get("extra", {}),
            },
        )
        return self.result(
            confidence=confidence,
            findings=findings or ["soil moisture within known thresholds"],
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority="P1" if risk == "high" else "P2",
        )
