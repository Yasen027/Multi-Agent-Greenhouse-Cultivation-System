"""基础专家 Agent 的并行评估入口。"""

import asyncio

from .crop_identification_agent import evaluate as evaluate_crop_identification

AGENTS = [
    "soil",
    "temperature",
    "humidity",
    "pest",
    "irrigation",
    "light_co2",
    "crop_stage",
]


async def evaluate(name, reading):
    """根据传感器读数生成单个领域 Agent 的规则结果。"""
    findings = []
    rec = []
    risk = "low"
    if name == "temperature" and reading.temperature > 30:
        findings.append("temperature high")
        rec.append("ventilation_on")
    if name == "humidity" and reading.humidity > 80:
        findings.append("humidity high")
        rec.append("ventilation_on")
    if name == "soil" and reading.soil_moisture < 30:
        findings.append("soil dry")
        rec.append("irrigation_on")
    if name == "pest" and reading.humidity > 90:
        findings.append("fungal risk")
        risk = "medium"
    return {
        "agent": name,
        "status": "ok",
        "confidence": 0.82,
        "findings": findings,
        "recommendations": rec,
        "risk_level": risk,
    }


async def run_all(reading):
    """并行运行全部专家，并追加作物识别结果。"""
    results = list(await asyncio.gather(*(evaluate(a, reading) for a in AGENTS)))
    results.append(await evaluate_crop_identification(reading))
    return results
