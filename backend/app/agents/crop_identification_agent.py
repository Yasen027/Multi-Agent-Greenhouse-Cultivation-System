"""作物识别 Agent 的兼容导入路径。"""

# 实际实现位于 app 包根目录，这里仅转发导出，保持 agents 包对外接口稳定。
from ..crop_identification_agent import (
    CROP_HINTS,
    build_prompt,
    evaluate,
    identify_crop,
)

__all__ = ["CROP_HINTS", "build_prompt", "evaluate", "identify_crop"]
