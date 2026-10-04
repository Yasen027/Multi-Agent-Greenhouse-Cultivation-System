from fastapi import APIRouter
from ..schemas import SensorReading
from .. import state
from ..services import audit
router=APIRouter(prefix='/api/sensors',tags=['sensors'])
@router.post('/readings')
def ingest(reading:SensorReading):
 state.latest=reading
 payload=reading.model_dump() if hasattr(reading,'model_dump') else reading.dict()
 state.history.insert(0,payload); del state.history[100:]
 audit('sensor_reading',payload); return reading
@router.get('/latest')
def latest(): return state.latest
