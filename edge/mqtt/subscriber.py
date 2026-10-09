import os

try:
    from .command_handler import subscribe
except ImportError:
    from command_handler import subscribe


if __name__ == "__main__":
    subscribe(
        os.getenv("MQTT_BROKER", "localhost"),
        os.getenv("MQTT_ACTUATOR_TOPIC", "greenhouse/actuators/commands"),
    )
