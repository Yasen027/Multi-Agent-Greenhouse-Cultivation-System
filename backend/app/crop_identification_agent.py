"""作物识别 Agent 与工具函数。"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .deepseek_client import DeepSeekError, deepseek_client
from .crop_profile import analyze_crop_conditions_async
from .prompt_loader import prompt_loader

logger = logging.getLogger(__name__)

# 作物名称提示词：用于从文件名/元数据中模糊匹配作物
CROP_HINTS = {
    'tomato': ('tomato', '番茄', '西红柿'),
    'lettuce': ('lettuce', '生菜'),
    'strawberry': ('strawberry', '草莓'),
    'cucumber': ('cucumber', '黄瓜'),
    'pepper': ('pepper', '辣椒'),
}

def build_prompt(context: Dict[str, Any]) -> str:
    return prompt_loader.load('crop_identification', context)

def _hitl(required: bool, reason: str = '', urgency: str = 'none') -> Dict[str, Any]:
    return {
        'required': required,
        'urgency': urgency if required else 'none',
        'reason': reason,
        'question_to_human': '请确认当前温室种植的作物和品种。' if required else '',
    }


def _normalize(result: Dict[str, Any], method: str) -> Dict[str, Any]:
    crop = str(result.get('crop') or result.get('crop_species') or 'unknown').lower().strip()
    # 中英文别名到标准作物键的映射
    aliases = {
        '西红柿': 'tomato',
        '番茄': 'tomato',
        'tomatoes': 'tomato',
        '生菜': 'lettuce',
        'lettuces': 'lettuce',
        '草莓': 'strawberry',
        'strawberries': 'strawberry',
        '黄瓜': 'cucumber',
        'cucumbers': 'cucumber',
        '辣椒': 'pepper',
        'peppers': 'pepper',
    }
    crop = aliases.get(crop, crop)
    try:
        confidence = max(0.0, min(1.0, float(result.get('confidence', 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    required = confidence < 0.7 or crop not in CROP_HINTS
    human = result.get('human_intervention') if isinstance(result.get('human_intervention'), dict) else {}
    human = _hitl(required, human.get('reason', '') or ('低置信度或未知作物' if required else ''), human.get('urgency', 'medium'))
    return {
        'crop': crop,
        'crop_species': result.get('crop_species') or crop,
        'crop_variety': result.get('crop_variety'),
        'crop_profile_key': crop if crop in CROP_HINTS else None,
        'confidence': confidence,
        'method': method,
        'evidence': result.get('evidence') or [],
        'human_intervention': human,
    }


def identify_crop(image_url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, user_input: str = '') -> Dict[str, Any]:
    metadata = metadata or {}
    prompt = build_prompt({
        'image_data': image_url or 'none',
        'user_input': user_input,
        'history_json': metadata.get('history', {}),
        'sensor_data_json': metadata.get('sensor_data', {}),
        'crop_knowledge_json': metadata.get('crop_knowledge', {}),
        'context': metadata,
    })
    try:
        response = deepseek_client.complete_json(prompt, image_url=image_url)
        return _normalize(response, 'deepseek_vision' if image_url else 'deepseek')
    except DeepSeekError as exc:
        logger.info('Using crop identification fallback: %s', exc)
    text = ' '.join([str(image_url or ''), str(metadata), user_input]).lower()
    for crop, hints in CROP_HINTS.items():
        if any(h in text for h in hints):
            return _normalize({'crop': crop, 'confidence': 0.92, 'evidence': text}, 'filename_or_metadata')
    return _normalize({'crop': 'unknown', 'confidence': 0.2, 'evidence': text}, 'fallback')

async def evaluate(reading) -> dict[str, Any]:
    """异步执行作物识别评估（供编排器/旧接口调用）。"""
    result = await asyncio.to_thread(
        identify_crop,
        getattr(reading, 'image_url', None),
        {'device_id': getattr(reading, 'device_id', '')},
    )
    profile = None
    # 识别成功且无需人工确认时，进一步分析作物环境档案
    if result['crop'] in CROP_HINTS and not result['human_intervention']['required']:
        profile = await analyze_crop_conditions_async(result['crop'])

    risk_level = 'low' if result['confidence'] >= 0.7 else 'medium'
    return {
        'agent': 'crop_identification',
        'status': 'ok',
        'confidence': result['confidence'],
        'findings': result,
        'recommendations': ['set_crop_profile'] if profile else ['request_human_confirmation'],
        'recommended_actions': ['设置当前作物档案'],
        'risk_level': risk_level,
        'crop': result['crop'],
        'method': result['method'],
        'human_intervention': result['human_intervention'],
        'crop_profile': profile,
    }
