# 安全兜底 Agent：对传感器读数与执行器指令做人工介入（HITL）风险评估。
class SafetyHITLAgent:
    def evaluate(self, reading, commands):
        reasons = []
        # 极端高温红线：与编排器 safety_rules 中的 temperature_max 一致。
        if reading.temperature > 40:
            reasons.append("温度超过 40℃，达到极端高温安全阈值")
        # pH 超出安全红线即触发人工介入。
        if reading.ph < 4 or reading.ph > 8:
            reasons.append("pH 超出 4～8 的安全范围")
        # 任何涉及农药的指令一律需人工确认。
        if any(c.get("actuator") == "pesticide" for c in commands):
            reasons.append("控制命令涉及化学农药")
        # 有任一理由则转为人工介入，否则放行。
        return {"status": "need_hitl" if reasons else "allow", "reasons": reasons}


# 全局安全评估单例，供 API 层与决策服务复用。
hitl_agent = SafetyHITLAgent()
