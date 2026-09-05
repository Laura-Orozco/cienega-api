from pydantic import BaseModel, Field
from datetime import datetime

class ESP32Payload(BaseModel):
    identificador: str = Field(..., example="ESP32_DEV_01")
    temperatura: float = Field(..., example=24.5)
    turbidez: float = Field(..., example=3.2)

class MeasurementResponse(BaseModel):
    id_medicion: int
    estado_calidad: str
    mensaje: str
    fecha_hora: datetime