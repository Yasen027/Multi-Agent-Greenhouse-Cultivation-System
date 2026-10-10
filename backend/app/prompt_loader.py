# Prompt 模板加载器：从 prompts 目录读取 Markdown 模板并做变量替换。
import json
from pathlib import Path
from typing import Any, Dict, Optional


class PromptLoader:
    """从新 prompts 目录加载模板，并兼容旧目录路径。"""

    def __init__(self, root: Optional[str] = None):
        if root:
            self.root = Path(root)
        else:
            # 模板目录候选顺序：backend/prompts 优先，其次 app/prompts；均不存在时回退到第一个候选。
            candidates = [
                Path(__file__).parents[1] / "prompts",
                Path(__file__).parent / "prompts",
            ]
            self.root = next(
                (path for path in candidates if path.exists()), candidates[0]
            )

    def load(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        # 读取指定模板；文件缺失时使用兜底文本，保证总能返回可用提示词。
        path = self.root / (name + ".md")
        text = (
            path.read_text(encoding="utf-8")
            if path.exists()
            else "Return valid structured JSON."
        )
        values = variables or {}
        # 显式传入的变量：字典/列表用 JSON 序列化，标量直接转字符串后替换。
        for key, value in values.items():
            rendered = (
                json.dumps(value, ensure_ascii=False, default=str)
                if isinstance(value, (dict, list, tuple))
                else str(value)
            )
            text = text.replace("{{" + key + "}}", rendered)
        # 不把未解析的模板变量发送给模型，也不让它们出现在审计记录中。
        for key in (
            "crop",
            "stage",
            "sensor_data_json",
            "history_json",
            "weather_json",
            "actuator_state",
            "agents_json",
            "safety_rules",
            "crop_profile_json",
            "user_input",
            "image_data",
            "context",
        ):
            text = text.replace(
                "{{" + key + "}}", "unknown" if key in ("crop", "stage") else "{}"
            )
        return text


# 进程级单例，供各决策服务复用。
prompt_loader = PromptLoader()
