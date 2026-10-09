from typing import Any


class BaseAgent:
    name = "base"
    prompt_name = ""

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def result(self, **kwargs):
        data = {
            "agent": self.name,
            "status": "ok",
            "confidence": 0.0,
            "findings": [],
            "recommendations": [],
            "risk_level": "low",
        }
        data.update(kwargs)
        return data
