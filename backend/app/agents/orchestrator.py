import asyncio
from typing import Any, Dict

from .. import state
from ..crop_identification_agent import evaluate as crop_identification
from ..prompt_loader import prompt_loader
from .registry import build_agents


def _dump(reading: Any) -> Dict[str, Any]:
    return reading.model_dump() if hasattr(reading, "model_dump") else reading.dict()


class Orchestrator:
    async def run(
        self,
        reading,
        crop_profile=None,
        history=None,
        weather=None,
        actuator_state=None,
    ):
        profile = crop_profile if isinstance(crop_profile, dict) else {}
        context = {
            "reading": reading,
            "crop_profile": profile,
            "sensor_data": _dump(reading),
            "history": history if history is not None else state.history,
            "weather": weather if weather is not None else state.weather,
            "actuator_state": (
                actuator_state if actuator_state is not None else state.actuator_state
            ),
            "extra": {},
        }
        agents = build_agents()
        variables = {
            "crop": profile.get("crop", "unknown"),
            "stage": profile.get("stage", "unknown"),
            "sensor_data_json": context["sensor_data"],
            "history_json": context["history"],
            "weather_json": context["weather"],
            "actuator_state": context["actuator_state"],
            "crop_profile_json": profile,
            "agents_json": [a.name for a in agents],
            "safety_rules": {
                "temperature_max": 40,
                "temperature_min": 5,
                "ph_min": 4,
                "ph_max": 8,
            },
        }
        self.last_prompt = prompt_loader.load("orchestrator", variables)
        results = list(await asyncio.gather(*(a.run(context) for a in agents)))
        # 作物识别由触发器控制；已有档案时不在每个传感器周期重复识别。
        if not profile.get("crop") and getattr(reading, "image_url", None):
            results.append(await crop_identification(reading))
        return results


orchestrator = Orchestrator()


async def run_all(
    reading, crop_profile=None, history=None, weather=None, actuator_state=None
):
    return await orchestrator.run(
        reading, crop_profile, history, weather, actuator_state
    )
