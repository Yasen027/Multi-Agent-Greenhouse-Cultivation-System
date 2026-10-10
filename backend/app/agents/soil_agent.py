# 土壤 Agent：评估 pH、电导率（EC）与土壤湿度并给出灌溉/调节建议。
from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class SoilAgent(BaseAgent):
    # 按作物档案中的目标 pH/EC 与湿度上下限做分级判断。
    name = "soil"
    prompt_name = "soil"

    async def run(self, context: dict[str, Any]):
        r = context["reading"]
        profile = context.get("crop_profile") or {}
        ph = r.ph
        findings = []
        actions = []
        risk = "low"
        confidence = 0.82
        # 目标值取自档案，缺省 pH 6.2 / EC 2.0。
        target_ph = float(profile.get("ph", 6.2)) if isinstance(profile, dict) else 6.2
        target_ec = float(profile.get("ec", 2.0)) if isinstance(profile, dict) else 2.0
        # pH 相对目标的绝对偏差，用于分级。
        delta = abs(ph - target_ph)
        # pH 极端异常（<4.5 或 >8.5）：最严重等级，转人工复核。
        if ph < 4.5 or ph > 8.5:
            findings.append("pH critical")
            risk = "critical"
            confidence = 0.65
            actions.append("human_review_soil")
        elif delta >= 0.8:
            # 偏差 ≥0.8：pH 严重偏离，高风险并建议调酸调碱。
            findings.append("pH severely deviated")
            risk = "high"
            actions.append("adjust_ph")
        elif delta >= 0.3:
            # 偏差 ≥0.3：pH 轻度偏离，中风险并建议调节。
            findings.append("pH warning")
            risk = "medium"
            actions.append("adjust_ph")
        # EC 超过目标 2 倍：临界，转人工复核；超过 1.3 倍：检查排水。
        if r.ec > target_ec * 2:
            findings.append("EC critical")
            risk = "critical"
            actions.append("human_review_soil")
            confidence = 0.65
        elif r.ec > target_ec * 1.3:
            findings.append("EC high")
            risk = "medium"
            actions.append("drainage_check")
        # 湿度上下限取自档案，缺省 30%～70%。
        moisture_min = (
            float(profile.get("soil_moisture_min", 30))
            if isinstance(profile, dict)
            else 30
        )
        moisture_max = (
            float(profile.get("soil_moisture_max", 70))
            if isinstance(profile, dict)
            else 70
        )
        if r.soil_moisture < moisture_min:
            # 低于下限：建议开启灌溉。
            findings.append("soil moisture low")
            actions.append("irrigation_on")
        elif r.soil_moisture > moisture_max:
            # 高于上限：建议停止灌溉，视为中等风险。
            findings.append("soil moisture high")
            actions.append("irrigation_off")
            risk = "medium"
        if not findings:
            # 全部指标正常时也给出明确结论。
            findings.append("soil within known thresholds")
        prompt = prompt_loader.load(
            "soil",
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
                "context": context.get("extra", {}),
            },
        )
        return self.result(
            confidence=confidence,
            findings=findings,
            recommendations=actions,
            risk_level=risk,
            prompt_loaded=bool(prompt),
        )
