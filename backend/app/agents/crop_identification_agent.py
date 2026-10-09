"""作物识别 Agent 的兼容导入路径。"""

from ..crop_identification_agent import (
    CROP_HINTS,
    build_prompt,
    evaluate,
    identify_crop,
)

__all__ = ["CROP_HINTS", "build_prompt", "evaluate", "identify_crop"]
