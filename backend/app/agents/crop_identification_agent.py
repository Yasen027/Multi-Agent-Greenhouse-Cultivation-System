from pathlib import Path
from typing import Any

CROP_HINTS = {
    'tomato': ('tomato', '番茄', '西红柿'),
    'lettuce': ('lettuce', '生菜'),
    'strawberry': ('strawberry', '草莓'),
    'cucumber': ('cucumber', '黄瓜'),
    'pepper': ('pepper', '辣椒'),
}

def identify_crop(image_url: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    text = ' '.join([str(image_url or ''), str(metadata or {})]).lower()
    for crop, hints in CROP_HINTS.items():
        if any(h in text for h in hints):
            return {'crop': crop, 'confidence': 0.92, 'method': 'filename_or_metadata', 'evidence': text}
    return {'crop': 'unknown', 'confidence': 0.2, 'method': 'fallback', 'evidence': text}

async def evaluate(reading) -> dict[str, Any]:
    result = identify_crop(getattr(reading, 'image_url', None), {'device_id': getattr(reading, 'device_id', '')})
    return {'agent': 'crop_identification', 'status': 'ok', 'confidence': result['confidence'], 'findings': [f"crop={result['crop']}"], 'recommendations': [], 'risk_level': 'low', 'crop': result['crop'], 'method': result['method']}
