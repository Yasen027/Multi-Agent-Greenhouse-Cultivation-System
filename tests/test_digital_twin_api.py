from fastapi.testclient import TestClient

from backend.app.main import app


def test_select_scenario_works_without_mqtt_broker(monkeypatch):
    monkeypatch.delenv("MQTT_BROKER", raising=False)
    with TestClient(app) as client:
        response = client.post("/api/digital-twin/scenario", json={"scenario": "cold_snap"})
        assert response.status_code == 200
        assert response.json()["status"] == "simulated_local"
        status = client.get("/api/digital-twin/status").json()
        assert status["scenario"] == "cold_snap"
        assert status["fault"] is None
        assert status["diagnostics"]["status"] == "healthy"
