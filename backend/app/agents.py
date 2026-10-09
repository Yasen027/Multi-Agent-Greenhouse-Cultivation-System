"""基于规则的简易 Agent 评估模块。

在完整 Agent 编排尚未接入时，提供基于阈值的快速评估。
"""

import asyncio

from .crop_identification_agent import evaluate as evaluate_crop_identification
from .schemas import SensorReading

# 参与常规评估的 Agent 名称
AGENTS = ['soil', 'temperature', 'humidity', 'pest', 'irrigation', 'light_co2', 'crop_stage']


async def evaluate(name, reading):
    """按名称对单条读数做阈值评估。"""
    findings = []
    rec = []
    risk = 'low'

    # 温度过高
    if name == 'temperature' and reading.temperature > 30:
        findings.append('temperature high')
        rec.append('ventilation_on')
    # 湿度过高
    if name == 'humidity' and reading.humidity > 80:
        findings.append('humidity high')
        rec.append('ventilation_on')
    # 土壤过干
    if name == 'soil' and reading.soil_moisture < 30:
        findings.append('soil dry')
        rec.append('irrigation_on')
    # 高湿引发真菌风险
    if name == 'pest' and reading.humidity > 90:
        findings.append('fungal risk')
        risk = 'medium'

    return {
        'agent': name,
        'status': 'ok',
        'confidence': 0.82,
        'findings': findings,
        'recommendations': rec,
        'risk_level': risk,
    }


async def run_all(reading):
    """并发评估所有 Agent，并追加作物识别结果。"""
    results = list(await asyncio.gather(*(evaluate(a, reading) for a in AGENTS)))
    results.append(await evaluate_crop_identification(reading))
    return results
