import asyncio

from backend.app.agents.decision_agent import decision_agent
from backend.app.agents.hitl_agent import hitl_agent
from backend.app.agents.orchestrator import run_all
from backend.app.crop_identification_agent import identify_crop
from backend.app.crop_profile import analyze_crop_conditions
from backend.app.deepseek_client import DeepSeekError, deepseek_client
from backend.app.schemas import SensorReading
from backend.app.services import safety
from backend.app.tools.actuator_tool import dispatch_commands


def test_identification_profile_orchestrator_fusion_chain(monkeypatch):
    monkeypatch.setattr(deepseek_client, 'complete_json', lambda *args, **kwargs: (_ for _ in ()).throw(DeepSeekError('offline')))
    identification = identify_crop(metadata={'note': 'tomato greenhouse'})
    assert identification['crop'] == 'tomato'
    assert identification['confidence'] >= 0.7
    profile = analyze_crop_conditions('tomato')
    reading = SensorReading(soil_moisture=20, temperature=32, image_url=None)
    outputs = asyncio.run(run_all(reading, profile))
    commands = decision_agent.fuse(outputs, {'crop_profile': profile})
    assert any(command['actuator'] == 'irrigation' for command in commands)
    assert safety(reading, commands)[0] == 'allow'
    assert hitl_agent.evaluate(reading, commands)['status'] == 'allow'
    assert dispatch_commands(commands)['status'] in ('skipped_no_broker', 'published', 'dispatch_failed')


def test_unknown_crop_requires_hitl(monkeypatch):
    monkeypatch.setattr(deepseek_client, 'complete_json', lambda *args, **kwargs: (_ for _ in ()).throw(DeepSeekError('offline')))
    result = identify_crop(image_url='unknown_crop.jpg')
    assert result['crop'] == 'unknown'
    assert result['human_intervention']['required'] is True
