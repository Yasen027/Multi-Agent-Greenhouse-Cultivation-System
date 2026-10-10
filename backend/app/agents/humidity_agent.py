# 湿度 Agent：按湿度阈值输出通风/喷雾建议，并评估结露与病害风险。
from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class HumidityAgent(BaseAgent):
    # 按档案湿度区间分级判断，湿度越高风险越大。
    name = "humidity"
    prompt_name = "humidity"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        # 目标湿度区间取自档案，缺省 50%～80%。
        target_min = (
            float(profile.get("humidity_min", 50)) if isinstance(profile, dict) else 50
        )
        target_max = (
            float(profile.get("humidity_max", 80)) if isinstance(profile, dict) else 80
        )
        # 湿度超过 95%：临界，伴随病害风险，通知虫害 Agent 并降低置信度。
        if r.humidity > 95:
            findings.append("humidity critical and disease risk")
            risk = "high"
            actions.extend(["ventilation_on", "notify_pest_agent"])
            confidence = 0.68
        elif r.humidity > target_max:
            # 高于目标上限：中等风险，建议通风。
            findings.append("humidity high")
            risk = "medium"
            actions.append("ventilation_on")
        elif r.humidity < target_min:
            # 低于目标下限：建议开启喷雾加湿。
            findings.append("humidity low")
            actions.append("mist_on")
        if not findings:
            findings.append("humidity within known thresholds")
        prompt = prompt_loader.load(
            "humidity",
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
            # 高风险/紧急提升为 P1，否则 P2。
            priority="P1" if risk in ("high", "emergency") else "P2",
            # vpd 暂未计算；湿度超过 90% 即视为存在结露风险。
            vpd=None,
            condensation_risk=r.humidity > 90,
        )
