import json
from pathlib import Path
from typing import Any, Dict, Optional


class PromptLoader:
    """从新 prompts 目录加载模板，并兼容旧目录路径。"""

    def __init__(self, root: Optional[str] = None):
        if root:
            self.root = Path(root)
        else:
            candidates = [
                Path(__file__).parents[1] / "prompts",
                Path(__file__).parent / "prompts",
            ]
            self.root = next(
                (path for path in candidates if path.exists()), candidates[0]
            )

    def load(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        path = self.root / (name + ".md")
        text = (
            path.read_text(encoding="utf-8")
            if path.exists()
            else "Return valid structured JSON."
        )
        values = variables or {}
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


prompt_loader = PromptLoader()
