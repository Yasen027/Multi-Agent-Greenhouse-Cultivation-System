from pydantic import BaseModel, Field
from datetime import datetime
from typing import Union, Optional
class SensorReading(BaseModel):
 device_id:str='simulator-1'; timestamp:datetime=Field(default_factory=datetime.utcnow); temperature:float=24; humidity:float=65; soil_moisture:float=45; ph:float=6.2; ec:float=1.5; light:float=500; co2:float=700; image_url:Optional[str]=None
class CropTriggerRequest(BaseModel):
 reason:str='manual'
 image_url:Optional[str]=None
 metadata:Optional[dict]=None
 force:bool=False
 interval_hours:Optional[int]=None
class ActuatorCommand(BaseModel):
 actuator:str; action:str; value:Optional[Union[float,str,bool]]=None; reason:str=''
