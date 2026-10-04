"""MQTT command consumer used by the edge runtime.

Hardware drivers can provide handlers for each actuator; the default handler
only records the command, making the module safe to run in simulation.
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)
ALLOWED_ACTUATORS = {'ventilation', 'irrigation', 'heating', 'mister', 'grow_light', 'shade', 'co2', 'fan'}


def handle_command(payload: Any, handlers: Optional[Dict[str, Callable[[str, Any], Any]]] = None) -> Dict[str, Any]:
    command = json.loads(payload) if isinstance(payload, (str, bytes, bytearray)) else payload
    if not isinstance(command, dict) or command.get('actuator') not in ALLOWED_ACTUATORS:
        raise ValueError('invalid actuator command')
    actuator, action = command['actuator'], command.get('action', 'off')
    value = command.get('value')
    handler = (handlers or {}).get(actuator)
    if handler:
        handler(action, value)
    logger.info('edge command applied: %s/%s', actuator, action)
    return {'status': 'applied', 'actuator': actuator, 'action': action, 'value': value}


def subscribe(broker: str = 'localhost', topic: str = 'greenhouse/actuators/commands', handlers=None):
    """Block in a paho loop and route validated commands to edge handlers."""
    import paho.mqtt.client as mqtt
    client = mqtt.Client()
    client.on_message = lambda _client, _userdata, message: handle_command(message.payload, handlers)
    client.connect(broker)
    client.subscribe(topic)
    client.loop_forever()
