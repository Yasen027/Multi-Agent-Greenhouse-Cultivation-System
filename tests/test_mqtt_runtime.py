import asyncio
from datetime import datetime, timedelta, timezone

from backend.app import state
from backend.app.decision_service import decision_service
from backend.app.device_health import (
    check_health,
    health_snapshot,
    prepare_commands,
    record_ack,
    reset_health,
)
from backend.app.mqtt_runtime import MqttRuntime
from backend.app.tools.actuator_dispatch import dispatch_commands


def _reset():
    reset_health()
    state.actuator_acks.clear()
    state.actuator_state.clear()
    state.hitl.clear()
    state.digital_twin.update(
        {"online": False, "scenario": None, "updated_at": None, "last_sensor_at": None}
    )


def test_mqtt_sensor_and_ack_update_shared_state():
    _reset()
    runtime = MqttRuntime()
    runtime._handle_sensor(
        {
            "device_id": "digital-twin-test",
            "temperature": 31,
            "humidity": 70,
            "soil_moisture": 25,
            "ph": 6.2,
            "ec": 1.5,
            "light": 500,
            "co2": 600,
            "_twin": {"online": True, "scenario": "hot_dry", "scenario_name": "高温干旱"},
        }
    )
    assert state.latest.device_id == "digital-twin-test"
    assert state.digital_twin["scenario"] == "hot_dry"

    runtime._handle_ack({"actuator": "irrigation", "action": "on", "status": "applied"})
    assert state.actuator_state["irrigation"] == "on"
    runtime._handle_ack({"actuator": "fan", "action": "on", "status": "failed"})
    assert state.actuator_state.get("fan") != "on"


def test_sensor_range_and_stuck_diagnostics_are_real():
    _reset()
    runtime = MqttRuntime()
    for index in range(3):
        accepted = runtime._handle_sensor(
            {
                "device_id": "stuck-test",
                "temperature": 25,
                "humidity": 60 + index,
                "soil_moisture": 40 + index,
                "ph": 6.2 + index * 0.1,
                "ec": 1.5 + index * 0.1,
                "light": 500 + index,
                "co2": 600 + index,
                "_twin": {"online": True, "scenario": "sensor_stuck"},
            }
        )
        assert accepted is True

    issues = health_snapshot()["sensor"]["issues"]
    assert any(issue["code"] == "sensor_stuck" for issue in issues)
    assert runtime._handle_sensor({"humidity": 999, "_twin": {"online": True}}) is False
    assert any(
        issue["code"] == "out_of_range"
        for issue in health_snapshot()["sensor"]["issues"]
    )


def test_sensor_offline_and_ack_deadline_are_diagnosed():
    _reset()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state.digital_twin["online"] = True
    state.sensor_monitor_started_at = now.isoformat()
    prepared, _ = prepare_commands(
        [{"actuator": "irrigation", "action": "on"}], now=now
    )

    diagnostics = check_health(now + timedelta(seconds=7))

    assert any(
        issue["code"] == "sensor_offline"
        for issue in diagnostics["sensor"]["issues"]
    )
    assert prepared[0]["command_id"] not in state.pending_acks
    assert state.actuator_acks[0]["status"] == "timeout"


def test_consecutive_failures_open_circuit_and_create_one_hitl():
    _reset()
    for _ in range(3):
        prepared, _ = prepare_commands([{"actuator": "fan", "action": "on"}])
        record_ack({**prepared[0], "status": "failed"})

    assert state.actuator_circuits["fan"] is True
    assert len([item for item in state.hitl if item["type"] == "device_failure"]) == 1
    dispatch = dispatch_commands([{"actuator": "fan", "action": "on"}])
    assert dispatch["status"] == "circuit_open"
    assert dispatch["suppressed"] == [{"actuator": "fan", "action": "on"}]

    request = next(item for item in state.hitl if item["type"] == "device_failure")
    asyncio.run(decision_service.approve_hitl(request["id"]))

    assert "fan" not in state.actuator_circuits
    assert not state.pending_acks
