from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class CropStageAgent(BaseAgent):
    name = "crop_stage"
    prompt_name = "crop_stage"

    async def run(self, context: dict[str, Any]):
        profile = context.get("crop_profile") or {}
        stage = (
            profile.get("stage", "unknown") if isinstance(profile, dict) else "unknown"
        )
        confidence = 0.8 if stage != "unknown" else 0.5
        prompt = prompt_loader.load(
            "crop_stage",
            {
                "crop": (
                    profile.get("crop", "unknown")
                    if isinstance(profile, dict)
                    else "unknown"
                ),
                "sensor_data_json": context["reading"].model_dump(),
                "history_json": context.get("history", {}),
                "crop_profile_json": profile,
                "context": context.get("extra", {}),
                "weather_json": context.get("weather", {}),
            },
        )
        return self.result(
            confidence=confidence,
            findings=[f"stage={stage}"],
            recommendations=["update_stage_thresholds"],
            risk_level="medium" if confidence < 0.7 else "low",
            prompt_loaded=bool(prompt),
            stage=stage,
        )
