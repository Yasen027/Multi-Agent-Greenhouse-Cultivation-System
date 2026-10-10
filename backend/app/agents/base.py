# 所有领域 Agent 的公共基类：定义统一的运行入口与结果结构。
from typing import Any


class BaseAgent:
    # 每个 Agent 的标识名与所加载提示词模板名，子类覆盖。
    name = "base"
    prompt_name = ""

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        # 子类必须实现：接收统一上下文，返回结构化结果。
        raise NotImplementedError

    def result(self, **kwargs):
        # 组装统一的 Agent 返回结构，允许子类用关键字参数覆盖默认字段。
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
