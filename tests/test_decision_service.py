import asyncio

from fastapi.testclient import TestClient

from backend.app import decision_service as service_module
from backend.app import state
from backend.app.device_health import record_sensor, reset_health
from backend.app.main import app
from backend.app.schemas import SensorReading


def _reset(reading=None):
    reset_health()
    state.digital_twin["online"] = False
    state.latest = reading or SensorReading()
    state.crop_profile = {"crop": "tomato", "confidence": 1.0}
    state.last_crop_identification = {}
    state.agent_cache.clear()
    state.decisions.clear()
    state.hitl.clear()
    state.actuator_state.clear()
    state.actuator_acks.clear()


def _agents(confidence=0.82):
    return [
        {
            "agent": "soil",
            "status": "ok",
            "confidence": confidence,
            "findings": [],
            "recommendations": ["irrigation_on"],
            "risk_level": "low",
        }
    ]


def test_service_normal_run_dispatches_and_returns_uniform_result(monkeypatch):
    _reset(SensorReading(soil_moisture=20))
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: {"status": "published", "count": len(commands)},
    )

    result = asyncio.run(service_module.decision_service.run(trigger="sensor"))

    assert isinstance(result, service_module.DecisionResult)
    assert isinstance(result.dispatch, service_module.DispatchResult)
    assert result.human_intervention is False
    assert result.dispatch.status == "published"
    assert "irrigation" not in state.actuator_state


def test_service_dangerous_reading_creates_hitl_and_never_dispatches(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: (_ for _ in ()).throw(
            AssertionError("unsafe commands dispatched")
        ),
    )

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert result.dispatch.status == "blocked_by_safety"
    assert state.hitl and state.hitl[0]["status"] == "pending"


def test_service_blocks_when_sensor_is_diagnosed_as_stuck(monkeypatch):
    reading = SensorReading(temperature=25)
    _reset(reading)
    for index in range(3):
        payload = reading.model_dump()
        payload["humidity"] += index
        payload["soil_moisture"] += index
        payload["ph"] += index * 0.1
        payload["ec"] += index * 0.1
        payload["light"] += index
        payload["co2"] += index
        record_sensor(payload)
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: (_ for _ in ()).throw(
            AssertionError("stuck sensor decision dispatched")
        ),
    )

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert "温度连续 3 次未变化，疑似卡死" in result.explanation_for_farmer
    assert result.dispatch.status == "blocked_by_safety"


def test_service_low_confidence_creates_hitl(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents(0.5))
    )

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is True
    assert "智能体置信度不足：土壤智能体" in result.explanation_for_farmer
    assert result.dispatch.status == "blocked_by_safety"


def test_service_preserves_dispatch_failure_result(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: {
            "status": "dispatch_failed",
            "count": len(commands),
            "error": "offline",
        },
    )

    result = asyncio.run(service_module.decision_service.run())

    assert result.human_intervention is False
    assert result.dispatch.to_dict() == {
        "status": "dispatch_failed",
        "count": 1,
        "error": "offline",
    }
    assert not state.actuator_state


def test_hitl_approve_uses_service_and_preserves_response(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    result = asyncio.run(service_module.decision_service.run())
    item = state.hitl[0]

    response = TestClient(app).post(f"/api/hitl/{item['id']}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["revalidation"]["dispatch"]["status"] == "simulated_local"
    assert state.actuator_acks[0]["status"] == "applied"
    assert state.hitl[0]["decision_id"] == result.id

    repeated = TestClient(app).post(f"/api/hitl/{item['id']}/approve")
    assert repeated.status_code == 409


def test_hitl_approval_recomputes_commands_from_latest_reading(monkeypatch):
    _reset(SensorReading(temperature=41, soil_moisture=20))
    runs = iter(
        [
            _agents(),
            [
                {
                    "agent": "temperature",
                    "status": "ok",
                    "confidence": 0.9,
                    "findings": [],
                    "recommendations": ["ventilation_on"],
                    "risk_level": "low",
                }
            ],
        ]
    )
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(next(runs))
    )
    dispatched = []
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: dispatched.extend(commands)
        or {"status": "published", "count": len(commands)},
    )
    asyncio.run(service_module.decision_service.run())
    item = state.hitl[0]
    state.latest = SensorReading(temperature=25, soil_moisture=45)

    response = TestClient(app).post(f"/api/hitl/{item['id']}/approve")

    assert response.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0]["actuator"] == "ventilation"
    assert dispatched[0]["action"] == "on"
    assert response.json()["revalidation"]["dispatch"]["status"] == "published"


def test_hitl_approval_requires_new_approval_when_risk_changes(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: (_ for _ in ()).throw(
            AssertionError("changed unsafe decision dispatched")
        ),
    )
    asyncio.run(service_module.decision_service.run())
    item = state.hitl[0]
    state.latest = SensorReading(temperature=41, ph=9)

    response = TestClient(app).post(f"/api/hitl/{item['id']}/approve")

    assert response.status_code == 200
    assert response.json()["revalidation"]["dispatch"]["status"] == "blocked_by_safety"
    pending = [request for request in state.hitl if request["status"] == "pending"]
    assert len(pending) == 1


def test_continuous_incident_creates_only_one_hitl_request(monkeypatch):
    _reset(SensorReading(temperature=41))
    monkeypatch.setattr(
        service_module, "run_all", lambda *args: _async_value(_agents())
    )
    monkeypatch.setattr(
        service_module,
        "dispatch_commands",
        lambda commands: {"status": "published", "count": len(commands)},
    )

    asyncio.run(service_module.decision_service.run())
    first = state.hitl[0]
    asyncio.run(service_module.decision_service.run())
    assert len(state.hitl) == 1

    service_module.decision_service.resolve_hitl(first["id"], "approved")
    asyncio.run(service_module.decision_service.run())
    assert len(state.hitl) == 1
    assert not [item for item in state.hitl if item["status"] == "pending"]

    asyncio.run(service_module.decision_service.run(SensorReading(temperature=25)))
    asyncio.run(service_module.decision_service.run(SensorReading(temperature=41)))
    assert len(state.hitl) == 2


def _async_value(value):
    async def _result():
        return value

    return _result()
