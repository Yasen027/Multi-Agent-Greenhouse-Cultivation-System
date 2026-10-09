"""专家 Agent 的抽象基类。

所有领域 Agent（土壤、温度、湿度、灌溉等）都继承 ``BaseAgent``，
并实现 ``run`` 方法，返回统一结构的分析结果字典。
"""

from typing import Any

from ..services import audit


class BaseAgent:
    """领域专家的公共基类。"""

    # 子类必须覆盖：Agent 唯一名称，用于结果与审计标记
    name = "base"

    # 子类必须覆盖：提示词模板名称，空字符串表示不需要加载提示词
    prompt_name = ""

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行一次分析，返回统一格式的结果字典。

        子类必须实现该方法；基类仅抛出 ``NotImplementedError``。
        """
        raise NotImplementedError

    def result(self, **kwargs) -> dict[str, Any]:
        """构造统一结构的 Agent 结果。

        先填入安全默认值，再用调用方传入的关键字参数覆盖，
        从而保证任何 Agent 返回的字段集合都保持一致。
        """
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
