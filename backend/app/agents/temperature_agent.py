from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class TemperatureAgent(BaseAgent):
    name = "temperature"
    prompt_name = "temperature"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        target_min = (
            float(profile.get("temperature_min", 18))
            if isinstance(profile, dict)
            else 18
        )
        target_max = (
            float(profile.get("temperature_max", 30))
            if isinstance(profile, dict)
            else 30
        )
        if r.temperature > 40 or r.temperature < 5:
            findings.append("temperature emergency")
            risk = "emergency"
            confidence = 0.65
            actions.append("human_review_temperature")
        elif r.temperature < target_min - 8 or r.temperature > target_max + 8:
            findings.append("temperature severely deviated")
            risk = "high"
            actions.append(
                "heating_on" if r.temperature < target_min else "ventilation_on"
            )
        elif r.temperature < target_min - 3 or r.temperature > target_max + 3:
            findings.append("temperature warning")
            risk = "medium"
            actions.append(
                "heating_on" if r.temperature < target_min else "ventilation_on"
            )
        elif r.temperature < target_min:
            actions.append("heating_on")
        elif r.temperature > target_max:
            actions.append("ventilation_on")
        if not findings:
            findings.append("temperature within known thresholds")
        prompt = prompt_loader.load(
            "temperature",
            {
                "stage": (
                    profile.get("stage", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "crop": (
                    profile.get("crop", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "crop_profile_json": profile,
                "sensor_data_json": r.model_dump(),
                "history_json": context.get("history", {}),
                "weather_json": context.get("weather", {}),
                "actuator_state": context.get("actuator_state", {}),
                "context": context.get("extra", {}),
            },
        )
        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority="P0" if risk == "emergency" else "P2",
        )
