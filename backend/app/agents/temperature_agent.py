# 温度 Agent：按作物档案的温度区间做分级判断，输出加热/通风建议。
from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class TemperatureAgent(BaseAgent):
    # 依据目标温度区间与偏离幅度给出 emergency/high/medium/low 风险等级。
    name = "temperature"
    prompt_name = "temperature"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        # 目标温度区间取自档案，缺省 18～30℃。
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
        # 超过 40℃ 或低于 5℃：极端红线（与安全规则一致），转人工复核。
        if r.temperature > 40 or r.temperature < 5:
            findings.append("temperature emergency")
            risk = "emergency"
            confidence = 0.65
            actions.append("human_review_temperature")
        elif r.temperature < target_min - 8 or r.temperature > target_max + 8:
            # 偏离目标区间超过 8℃：严重偏离，高优先级加热/通风。
            findings.append("temperature severely deviated")
            risk = "high"
            actions.append(
                "heating_on" if r.temperature < target_min else "ventilation_on"
            )
        elif r.temperature < target_min - 3 or r.temperature > target_max + 3:
            # 偏离目标区间超过 3℃：轻度告警，中风险。
            findings.append("temperature warning")
            risk = "medium"
            actions.append(
                "heating_on" if r.temperature < target_min else "ventilation_on"
            )
        elif r.temperature < target_min:
            # 未超 3℃ 但低于目标下限：仅建议加热，不计为发现。
            actions.append("heating_on")
        elif r.temperature > target_max:
            # 未超 3℃ 但高于目标上限：仅建议通风，不计为发现。
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
            # 紧急情况标记 P0 最高优先级，否则 P2。
            priority="P0" if risk == "emergency" else "P2",
        )
