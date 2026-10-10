"""最小可解释温室模型：执行器状态直接驱动下一周期环境变化。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import random
from typing import Any


# 预定义场景库：每个场景包含名称、说明、初始环境、外界环境以及可选的故障注入配置。
SCENARIOS: dict[str, dict[str, Any]] = {
    "normal": {
        "name": "正常生产",
        "description": "环境稳定，用于演示常规闭环。",
        "initial": {"temperature": 25, "humidity": 68, "soil_moisture": 48, "ph": 6.2, "ec": 1.8, "light": 650, "co2": 650},
        "ambient": {"temperature": 27, "humidity": 62, "light": 700, "co2": 430},
    },
    "hot_dry": {
        "name": "高温干旱",
        "description": "高温、湿度偏高且土壤缺水，触发通风和灌溉。",
        "initial": {"temperature": 35, "humidity": 84, "soil_moisture": 24, "ph": 6.2, "ec": 1.8, "light": 900, "co2": 650},
        "ambient": {"temperature": 38, "humidity": 75, "light": 1000, "co2": 430},
    },
    "cold_snap": {
        "name": "低温寒潮",
        "description": "温度持续偏低，触发加热。",
        "initial": {"temperature": 12, "humidity": 72, "soil_moisture": 46, "ph": 6.2, "ec": 1.8, "light": 450, "co2": 600},
        "ambient": {"temperature": 8, "humidity": 74, "light": 400, "co2": 430},
    },
    "low_light_co2": {
        "name": "弱光低 CO₂",
        "description": "光照和 CO₂ 不足，用于演示补光、补气效果。",
        "initial": {"temperature": 23, "humidity": 66, "soil_moisture": 48, "ph": 6.2, "ec": 1.8, "light": 80, "co2": 280},
        "ambient": {"temperature": 24, "humidity": 64, "light": 100, "co2": 360},
    },
    "actuator_failed": {
        "name": "风机故障",
        "description": "风机/通风命令返回 failed，环境不会产生对应变化。",
        "initial": {"temperature": 35, "humidity": 86, "soil_moisture": 45, "ph": 6.2, "ec": 1.8, "light": 800, "co2": 650},
        "ambient": {"temperature": 37, "humidity": 78, "light": 900, "co2": 430},
        "actuator_faults": {"fan": "failed", "ventilation": "failed"},
    },
    "actuator_timeout": {
        "name": "灌溉无响应",
        "description": "灌溉命令不返回 ACK，土壤湿度不变化。",
        "initial": {"temperature": 26, "humidity": 68, "soil_moisture": 22, "ph": 6.2, "ec": 1.8, "light": 600, "co2": 600},
        "ambient": {"temperature": 28, "humidity": 62, "light": 700, "co2": 430},
        "actuator_faults": {"irrigation": "timeout"},
    },
    "sensor_stuck": {
        "name": "传感器固定值",
        "description": "温度传感器固定在 25℃，用于演示卡死诊断。",
        "initial": {"temperature": 33, "humidity": 75, "soil_moisture": 42, "ph": 6.2, "ec": 1.8, "light": 650, "co2": 650},
        "ambient": {"temperature": 36, "humidity": 70, "light": 700, "co2": 430},
        "sensor_fault": {"mode": "fixed", "sensor": "temperature", "value": 25.0},
    },
    "sensor_abnormal": {
        "name": "传感器异常值",
        "description": "湿度传感器输出 999%，用于演示异常值识别。",
        "initial": {"temperature": 25, "humidity": 68, "soil_moisture": 45, "ph": 6.2, "ec": 1.8, "light": 650, "co2": 650},
        "ambient": {"temperature": 27, "humidity": 62, "light": 700, "co2": 430},
        "sensor_fault": {"mode": "abnormal", "sensor": "humidity", "value": 999.0},
    },
    "sensor_timeout": {
        "name": "传感器超时",
        "description": "停止发布传感器数据，但孪生状态仍在线。",
        "initial": {"temperature": 25, "humidity": 68, "soil_moisture": 45, "ph": 6.2, "ec": 1.8, "light": 650, "co2": 650},
        "ambient": {"temperature": 27, "humidity": 62, "light": 700, "co2": 430},
        "sensor_fault": {"mode": "timeout"},
    },
}


# 数字孪生核心对象：持有当前场景的环境状态、执行器状态与仿真周期计数。
@dataclass
class DigitalTwin:
    scenario: str = "normal"
    device_id: str = "digital-twin-1"
    values: dict[str, float] = field(init=False)
    actuators: dict[str, str] = field(default_factory=dict)
    cycle: int = 0

    # dataclass 构造完成后立即按默认场景加载初始环境。
    def __post_init__(self) -> None:
        self.select_scenario(self.scenario)

    # 当前场景的完整配置字典（含 initial/ambient/故障注入）。
    @property
    def config(self) -> dict[str, Any]:
        return SCENARIOS[self.scenario]

    # 切换场景：校验名称后重置环境状态、执行器状态与周期计数。
    def select_scenario(self, scenario: str) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {scenario}")
        self.scenario = scenario
        # 深拷贝初始环境值，避免后续仿真修改污染场景定义。
        self.values = deepcopy(SCENARIOS[scenario]["initial"])
        self.actuators = {}
        self.cycle = 0

    # 处理一条执行器命令：先检查故障注入，再校验执行器白名单，最后更新状态并返回 ACK。
    def apply_command(self, command: dict[str, Any]) -> dict[str, Any] | None:
        actuator = str(command.get("actuator", ""))
        action = str(command.get("action", "off"))
        # 查询该执行器在当前场景下的故障注入类型。
        fault = self.config.get("actuator_faults", {}).get(actuator)
        # timeout 故障：模拟设备无响应，返回 None 表示不产生任何 ACK。
        if fault == "timeout":
            return None
        # failed 故障：模拟设备故障，返回带错误说明的失败 ACK。
        if fault == "failed":
            return self._ack(command, "failed", "simulated device failure")
        # 不在支持列表中的执行器直接返回 failed ACK。
        if actuator not in {"ventilation", "fan", "irrigation", "heating", "grow_light", "co2", "mister", "shade"}:
            return self._ack(command, "failed", "unknown actuator")
        # 正常命令：记录执行器状态并返回 applied ACK。
        self.actuators[actuator] = action
        return self._ack(command, "applied")

    def step(self) -> dict[str, float]:
        """推进一个仿真周期；变化量故意直观，便于比赛现场观察。"""
        # 一阶趋近模型：各环境变量按固定比例向外界环境靠拢，不同变量收敛速率不同。
        ambient = self.config["ambient"]
        self.values["temperature"] += (ambient["temperature"] - self.values["temperature"]) * 0.04
        self.values["humidity"] += (ambient["humidity"] - self.values["humidity"]) * 0.04
        self.values["light"] += (ambient["light"] - self.values["light"]) * 0.08
        self.values["co2"] += (ambient["co2"] - self.values["co2"]) * 0.05
        # 土壤湿度每周期自然蒸发下降 0.12。
        self.values["soil_moisture"] -= 0.12

        # 风机或通风开启：降温并带走部分湿度。
        if self._on("fan") or self._on("ventilation"):
            self.values["temperature"] -= 0.55
            self.values["humidity"] -= 1.0
        # 灌溉开启：显著提升土壤湿度。
        if self._on("irrigation"):
            self.values["soil_moisture"] += 2.2
        # 加热开启：温度上升。
        if self._on("heating"):
            self.values["temperature"] += 0.65
        # 补光灯开启：光照大幅增强。
        if self._on("grow_light"):
            self.values["light"] += 260
        # CO₂ 补充开启：浓度提升。
        if self._on("co2"):
            self.values["co2"] += 55
        # 喷雾开启：湿度上升。
        if self._on("mister"):
            self.values["humidity"] += 1.2
        # 遮阳开启：光照下降。
        if self._on("shade"):
            self.values["light"] -= 180

        # 对各项状态做上下限裁剪，防止长时间仿真后数值越界（温度 -10~60，湿度与土壤湿度 0~100，光照与 CO₂ 不低于 0）。
        self.values["temperature"] = min(60, max(-10, self.values["temperature"]))
        self.values["humidity"] = min(100, max(0, self.values["humidity"]))
        self.values["soil_moisture"] = min(100, max(0, self.values["soil_moisture"]))
        self.values["light"] = max(0, self.values["light"])
        self.values["co2"] = max(0, self.values["co2"])
        # 周期计数递增，并返回深拷贝后的环境状态。
        self.cycle += 1
        return deepcopy(self.values)

    # 生成对外发布的传感器报文；按场景的传感器故障注入决定改写或置空。
    def sensor_payload(self) -> dict[str, Any] | None:
        # 读取当前场景的传感器故障注入配置。
        fault = self.config.get("sensor_fault", {})
        # timeout 故障：不发布任何传感器数据（模拟传感器失联）。
        if fault.get("mode") == "timeout":
            return None
        # 在真实值上叠加 ±0.04 的随机噪声，模拟传感器测量误差。
        values = {key: round(value + random.uniform(-0.04, 0.04), 2) for key, value in self.values.items()}
        # fixed/abnormal 故障：把指定传感器的读数直接改写为故障值。
        if fault.get("mode") in {"fixed", "abnormal"}:
            values[fault["sensor"]] = fault["value"]
        return {
            # 报文附带设备标识、UTC 时间戳与孪生自身状态，便于后端关联。
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **values,
            "_twin": self.status(),
        }

    # 汇总孪生在线状态、场景信息、执行器状态与当前环境读数。
    def status(self) -> dict[str, Any]:
        # 优先携带传感器故障，其次执行器故障；两者皆无时为 None。
        fault = self.config.get("sensor_fault") or self.config.get("actuator_faults") or None
        return {
            "online": True,
            "scenario": self.scenario,
            "scenario_name": self.config["name"],
            "cycle": self.cycle,
            "actuators": deepcopy(self.actuators),
            "environment": {key: round(value, 2) for key, value in self.values.items()},
            "fault": deepcopy(fault),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # 判断某执行器当前是否处于开启状态。
    def _on(self, actuator: str) -> bool:
        return self.actuators.get(actuator) == "on"

    # 构造标准 ACK 报文；error 字段仅在存在错误说明时附带。
    @staticmethod
    def _ack(command: dict[str, Any], status: str, error: str | None = None) -> dict[str, Any]:
        ack = {
            "command_id": command.get("command_id"),
            "actuator": command.get("actuator"),
            "action": command.get("action"),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            ack["error"] = error
        return ack
