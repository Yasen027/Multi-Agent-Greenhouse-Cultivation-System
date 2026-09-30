from fastapi import APIRouter
from ..schemas import SensorReading
from .. import state
from ..services import audit
router=APIRouter(prefix='/api/sensors',tags=['sensors'])
@router.post('/readings')
def ingest(reading:SensorReading):
 state.latest=reading; audit('sensor_reading',reading.model_dump()); return reading
@router.get('/latest')
def latest(): return state.latest
