"""作物生长阶段分析 Agent。

根据当前作物档案推断作物所处生长阶段，
输出统一格式的 Agent 结果。
"""

from typing import Any

from ..prompt_loader import prompt_loader
from .base import BaseAgent


class CropStageAgent(BaseAgent):
    """作物生长阶段判断专家。"""

    name = 'crop_stage'
    prompt_name = 'crop_stage'

    async def run(self, context: dict[str, Any]):
        # 提取作物档案与当前阶段
        profile = context.get('crop_profile') or {}
        if isinstance(profile, dict):
            stage = profile.get('stage', 'unknown')
        else:
            stage = 'unknown'
        # 阶段已知时置信度更高
        confidence = 0.8 if stage != 'unknown' else 0.5

        # 加载阶段提示词
        crop = profile.get('crop', 'unknown') if isinstance(profile, dict) else 'unknown'
        prompt = prompt_loader.load('crop_stage', {
            'crop': crop,
            'sensor_data_json': context['reading'].model_dump(),
            'history_json': context.get('history', {}),
            'crop_profile_json': profile,
            'context': context.get('extra', {}),
            'weather_json': context.get('weather', {}),
        })

        # 风险等级：置信度偏低时标记为 medium
        risk_level = 'medium' if confidence < 0.7 else 'low'
        return self.result(
            confidence=confidence,
            findings=[f'stage={stage}'],
            recommendations=['update_stage_thresholds'],
            risk_level=risk_level,
            prompt_loaded=bool(prompt),
            stage=stage,
        )
