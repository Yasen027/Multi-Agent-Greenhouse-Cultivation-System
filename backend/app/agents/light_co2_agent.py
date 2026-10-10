# 光照与 CO2 Agent：评估光照强度与 CO2 浓度，输出补光/遮阳/补碳建议。
from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class LightCO2Agent(BaseAgent):
    # 光照低于下限补光；光照过高且伴随高温时遮阳；CO2 不足给出补碳复核建议。
    name = "light_co2"
    prompt_name = "light_co2"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        # 光照上下限取自档案，缺省 200～1200 lux。
        light_min = (
            float(profile.get("light_min", 200)) if isinstance(profile, dict) else 200
        )
        light_max = (
            float(profile.get("light_max", 1200)) if isinstance(profile, dict) else 1200
        )
        # CO2 下限取自档案，缺省 350 ppm。
        co2_min = (
            float(profile.get("co2_min", 350)) if isinstance(profile, dict) else 350
        )
        # 光照不足：建议开启补光灯。
        if r.light < light_min:
            findings.append("light low")
            actions.append("supplemental_light_on")
        # 光照过强且同时超过温度上限：强光叠加高温，建议遮阳。
        if r.light > light_max and r.temperature > float(
            profile.get("temperature_max", 30)
        ):
            findings.append("excessive light with heat")
            actions.append("shade_on")
            risk = "medium"
        # CO2 浓度不足：建议复核后补充 CO2（涉及安全，仅给复核建议）。
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
            # 该 Agent 始终使用 P2 默认优先级。
            priority="P2",
        )
