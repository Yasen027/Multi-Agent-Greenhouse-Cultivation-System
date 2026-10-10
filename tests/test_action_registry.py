import asyncio

from fastapi.testclient import TestClient

from backend.app import decision_service as service_module
from backend.app import state
from backend.app.action_registry import (
    ACTION_REGISTRY,
    ALLOWED_ACTUATORS,
    action_alert,
    command_conflicts,
)
from backend.app.agents.decision_agent import decision_agent
from backend.app.main import app
from backend.app.schemas import SensorReading
from backend.app.tools.actuator_dispatch import dispatch_commands
from backend.app.services import safety


def test_all_agent_recommendations_are_registered_and_structured():
    recommendations = {
        "ventilation_on",
        "ventilation_off",
        "irrigation_on",
        "irrigation_off",
        "heating_on",
        "heating_off",
        "mist_on",
        "supplemental_light_on",
        "shade_on",
        "co2_on",
        "fan_on",
        "fan_off",
        "adjust_ph",
        "drainage_check",
        "human_review_soil",
        "human_review_temperature",
        "human_review_irrigation",
        "notify_pest_agent",
        "co2_enrichment_review",
        "update_stage_thresholds",
        "set_crop_profile",
        "request_human_confirmation",
    }
    assert recommendations <= ACTION_REGISTRY.keys()
    assert all(action_alert(name)["message"] for name in recommendations)


def test_unknown_recommendation_is_not_dropped():
    assert (
        decision_agent.fuse([{"agent": "test", "recommendations": ["unknown_action"]}])
        == []
    )
    assert decision_agent.last_alerts[0]["type"] == "unknown_recommendation"
    assert decision_agent.last_alerts[0]["requires_hitl"] is True


def test_high_risk_actions_require_hitl_and_commands_share_whitelist():
    _commands = decision_agent.fuse(
        [{"agent": "test", "recommendations": ["pesticide_on"]}]
    )
    assert ACTION_REGISTRY["pesticide_on"].requires_hitl is True
    assert decision_agent.last_alerts[0]["requires_hitl"] is True
    assert "pesticide" not in ALLOWED_ACTUATORS
    assert command_conflicts(
        [
            {"actuator": "heating", "action": "on"},
            {"actuator": "ventilation", "action": "on"},
        ]
    )
    assert (
        dispatch_commands([{"actuator": "pesticide", "action": "on"}])["status"]
        == "blocked_unsafe_actuator"
    )


def test_service_surfaces_registered_alerts_and_blocks_high_risk_action(monkeypatch):
    state.latest = SensorReading()
    state.crop_profile = {"crop": "tomato", "confidence": 1.0}
    state.last_crop_identification = {}
    state.agent_cache.clear()
    state.decisions.clear()
    state.hitl.clear()
    monkeypatch.setattr(
        service_module,
        "run_all",
        lambda *args: _async_value(
            [{"agent": "soil", "confidence": 0.82, "recommendations": ["adjust_ph"]}]
        ),
    )

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert result.dispatch.status == "blocked_by_safety"
    assert result.action_alerts[0]["recommendation"] == "adjust_ph"
    assert state.hitl


def test_manual_commands_use_registry_and_shared_safety_gate():
    state.latest = SensorReading()
    state.hitl.clear()
    client = TestClient(app)

    allowed = client.post(
        "/api/actuators/command", json={"actuator": "irrigation", "action": "on"}
    )
    pesticide = client.post(
        "/api/actuators/command", json={"actuator": "pesticide", "action": "on"}
    )
    unknown = client.post(
        "/api/actuators/command", json={"actuator": "unknown", "action": "on"}
    )

    assert allowed.json()["status"] == "accepted"
    assert pesticide.json()["status"] == "need_hitl"
    assert pesticide.json()["alerts"][0]["recommendation"] == "pesticide_on"
    assert unknown.json()["code"] == "unknown_recommendation"


def test_all_human_approval_reasons_are_chinese():
    messages = [
        spec.message
        for spec in ACTION_REGISTRY.values()
        if spec.requires_hitl
    ]
    messages.extend(safety(SensorReading(temperature=41, ph=9), [])[1])
    assert messages
    assert all(any("\u4e00" <= char <= "\u9fff" for char in message) for message in messages)


def _async_value(value):
    async def _result():
        return value

    return _result()
