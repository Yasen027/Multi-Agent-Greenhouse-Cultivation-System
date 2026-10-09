from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class LightCO2Agent(BaseAgent):
    name = "light_co2"
    prompt_name = "light_co2"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        light_min = (
            float(profile.get("light_min", 200)) if isinstance(profile, dict) else 200
        )
        light_max = (
            float(profile.get("light_max", 1200)) if isinstance(profile, dict) else 1200
        )
        co2_min = (
            float(profile.get("co2_min", 350)) if isinstance(profile, dict) else 350
        )
        if r.light < light_min:
            findings.append("light low")
            actions.append("supplemental_light_on")
        if r.light > light_max and r.temperature > float(
            profile.get("temperature_max", 30)
        ):
            findings.append("excessive light with heat")
            actions.append("shade_on")
            risk = "medium"
        if r.co2 < co2_min:
            findings.append("co2 low")
            actions.append("co2_enrichment_review")
        prompt = prompt_loader.load(
            "light_co2",
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
            findings=findings or ["light and co2 within known thresholds"],
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
            priority="P2",
        )
