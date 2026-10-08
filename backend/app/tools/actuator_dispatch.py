"""Best-effort MQTT bridge for commands that already passed safety review."""

import json
import logging
import os
from typing import Any, Dict, Iterable
from ..action_registry import ALLOWED_ACTUATORS

logger = logging.getLogger(__name__)
def dispatch_commands(commands: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    commands = list(commands or [])
    unsafe = [command for command in commands if command.get('actuator') not in ALLOWED_ACTUATORS]
    if unsafe:
        return {'status': 'blocked_unsafe_actuator', 'count': 0, 'rejected': unsafe}
    broker = os.getenv('MQTT_BROKER', '')
    if not commands:
        return {'status': 'nothing_to_dispatch', 'count': 0}
    if not broker:
        return {'status': 'skipped_no_broker', 'count': len(commands)}
    try:
        import paho.mqtt.publish as publish
        topic = os.getenv('MQTT_ACTUATOR_TOPIC', 'greenhouse/actuators/commands')
        publish.multiple([{'topic': topic, 'payload': json.dumps(command, ensure_ascii=False)} for command in commands], hostname=broker)
        return {'status': 'published', 'count': len(commands), 'topic': topic}
    except Exception as exc:
        logger.warning('MQTT dispatch failed: %s', exc)
        return {'status': 'dispatch_failed', 'count': len(commands), 'error': str(exc)}
