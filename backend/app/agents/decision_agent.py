"""决策融合 Agent。

汇总各领域 Agent 的建议，映射为可执行的执行器指令，
并对需要人工介入的动作发出告警。
"""

from ..action_registry import action_alert, get_action
from ..prompt_loader import prompt_loader
from ..schemas import ActuatorCommand


class DecisionFusionAgent:
    """融合专家建议并生成执行器指令。"""

    def fuse(self, outputs, context=None):
        context = context or {}
        profile = context.get("crop_profile") or {}
        self.last_alerts = []
        self.last_hitl_actions = []

        commands = []
        seen = set()
        for agent in outputs or []:
            for rec in agent.get("recommendations", []) or []:
                spec = get_action(rec)
                # 未知建议：记录告警并加入人工介入列表
                if spec is None:
                    self.last_alerts.append(
                        action_alert(rec, agent.get("agent", "agent"))
                    )
                    self.last_hitl_actions.append(rec)
                    continue
                # 非指令动作且无执行器：仅记录告警
                if spec.kind != "command" and not spec.actuator:
                    alert = action_alert(rec, agent.get("agent", "agent"))
                    self.last_alerts.append(alert)
                    if spec.requires_hitl:
                        self.last_hitl_actions.append(rec)
                    continue
                # 按执行器+动作去重，避免重复下发
                actuator, action = spec.actuator, spec.action
                key = (actuator, action)
                if key in seen:
                    continue
                seen.add(key)
                command = ActuatorCommand(
                    actuator=actuator,
                    action=action,
                    reason=agent.get("agent", "agent"),
                )
                command_data = (
                    command.model_dump()
                    if hasattr(command, "model_dump")
                    else command.dict()
                )
                commands.append(command_data)
                # 需要人工介入的动作
                if spec.requires_hitl:
                    self.last_hitl_actions.append(rec)
                    self.last_alerts.append(
                        action_alert(rec, agent.get("agent", "agent"))
                    )

        # 加载决策融合提示词
        self.last_prompt = prompt_loader.load(
            "decision_fusion",
            {
                "crop": context.get("crop", profile.get("crop", "unknown")),
                "stage": context.get("stage", profile.get("stage", "unknown")),
                "crop_profile_json": profile,
                "agents_json": outputs or [],
                "actuator_state": context.get("actuator_state", {}),
                "safety_rules": context.get("safety_rules", {}),
            },
        )
        return commands


# 全局决策融合单例
decision_agent = DecisionFusionAgent()
