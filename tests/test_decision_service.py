import asyncio

from fastapi.testclient import TestClient

from backend.app import decision_service as service_module
from backend.app import state
from backend.app.main import app
from backend.app.schemas import SensorReading


def _reset(reading=None):
    state.latest = reading or SensorReading()
    state.crop_profile = {"crop": "tomato", "confidence": 1.0}
    state.last_crop_identification = {}
    state.agent_cache.clear()
    state.decisions.clear()
    state.hitl.clear()
    state.actuator_state.clear()


def _agents(confidence=0.82):
    return [{
        "agent": "soil",
        "status": "ok",
        "confidence": confidence,
        "findings": [],
        "recommendations": ["irrigation_on"],
        "risk_level": "low",
    }]


def test_service_normal_run_dispatches_and_returns_uniform_result(monkeypatch):
    _reset(SensorReading(soil_moisture=20))
    monkeypatch.setattr(service_module, "run_all", lambda *args: _async_value(_agents()))
    monkeypatch.setattr(service_module, "dispatch_commands", lambda commands: {"status": "published", "count": len(commands)})

    result = asyncio.run(service_module.decision_service.run(trigger="sensor"))

    assert isinstance(result, service_module.DecisionResult)
    assert isinstance(result.dispatch, service_module.DispatchResult)
    assert result.human_intervention is False
    assert result.dispatch.status == "published"
    assert state.actuator_state["irrigation"] == "on"


def test_service_dangerous_reading_creates_hitl_and_never_dispatches(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(service_module, "run_all", lambda *args: _async_value(_agents()))
    monkeypatch.setattr(service_module, "dispatch_commands", lambda commands: (_ for _ in ()).throw(AssertionError("unsafe commands dispatched")))

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert result.dispatch.status == "blocked_by_safety"
    assert state.hitl and state.hitl[0]["status"] == "pending"


def test_service_low_confidence_creates_hitl(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "run_all", lambda *args: _async_value(_agents(0.5)))

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert "low confidence agents: soil" in result.explanation_for_farmer
    assert result.dispatch.status == "blocked_by_safety"


def test_service_preserves_dispatch_failure_result(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "run_all", lambda *args: _async_value(_agents()))
    monkeypatch.setattr(service_module, "dispatch_commands", lambda commands: {"status": "dispatch_failed", "count": len(commands), "error": "offline"})

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is False
    assert result.dispatch.to_dict() == {"status": "dispatch_failed", "count": 1, "error": "offline"}
    assert not state.actuator_state


def test_hitl_approve_uses_service_and_preserves_response(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(service_module, "run_all", lambda *args: _async_value(_agents()))
    result = asyncio.run(service_module.decision_service.run())
    item = state.hitl[0]

    response = TestClient(app).post(f"/api/hitl/{item['id']}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert state.hitl[0]["decision_id"] == result.id


def _async_value(value):
    async def _result():
        return value

    return _result()
