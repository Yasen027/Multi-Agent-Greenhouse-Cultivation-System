from digital_twin.engine import DigitalTwin


def test_actuators_change_the_next_environment_cycle():
    expected = {
        "fan": ("temperature", "down"),
        "irrigation": ("soil_moisture", "up"),
        "heating": ("temperature", "up"),
        "grow_light": ("light", "up"),
        "co2": ("co2", "up"),
    }
    for actuator, (sensor, direction) in expected.items():
        twin = DigitalTwin("normal")
        before = twin.values.copy()
        assert twin.apply_command({"actuator": actuator, "action": "on"})["status"] == "applied"
        after = twin.step()
        assert (after[sensor] > before[sensor]) is (direction == "up")
    fan = DigitalTwin("normal")
    before_humidity = fan.values["humidity"]
    fan.apply_command({"actuator": "fan", "action": "on"})
    assert fan.step()["humidity"] < before_humidity


def test_failure_scenarios_cover_failed_no_response_and_sensor_faults():
    failed = DigitalTwin("actuator_failed")
    assert failed.apply_command({"actuator": "fan", "action": "on"})["status"] == "failed"
    timeout = DigitalTwin("actuator_timeout")
    assert timeout.apply_command({"actuator": "irrigation", "action": "on"}) is None
    stuck = DigitalTwin("sensor_stuck")
    stuck.step()
    assert stuck.sensor_payload()["temperature"] == 25.0
    assert DigitalTwin("sensor_abnormal").sensor_payload()["humidity"] == 999.0
    assert DigitalTwin("sensor_timeout").sensor_payload() is None
