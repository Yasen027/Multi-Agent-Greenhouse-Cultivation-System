import json
from pathlib import Path
from typing import Any, Dict, Optional


class PromptLoader:
    """Load prompts from the new backend/prompts directory with old-path support."""

    def __init__(self, root: Optional[str] = None):
        if root:
            self.root = Path(root)
        else:
            candidates = [Path(__file__).parents[1] / "prompts", Path(__file__).parent / "prompts"]
            self.root = next((path for path in candidates if path.exists()), candidates[0])

    def load(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        path = self.root / (name + ".md")
        text = path.read_text(encoding="utf-8") if path.exists() else "Return valid structured JSON."
        values = variables or {}
        for key, value in values.items():
            rendered = json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list, tuple)) else str(value)
            text = text.replace("{{" + key + "}}", rendered)
        # Never send unresolved template tokens to a model or expose them in audits.
        for key in ("crop", "stage", "sensor_data_json", "history_json", "weather_json", "actuator_state", "agents_json", "safety_rules", "crop_profile_json", "user_input", "image_data", "context"):
            text = text.replace("{{" + key + "}}", "unknown" if key in ("crop", "stage") else "{}")
        return text


prompt_loader = PromptLoader()
