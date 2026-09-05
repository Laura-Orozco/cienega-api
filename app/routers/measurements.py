from fastapi import APIRouter, HTTPException, Request, Query, status
from typing import Optional
from app.schemas.measurement import ESP32Payload, MeasurementResponse
from app.services.water_service import WaterQualityService

router = APIRouter(prefix="/api/mediciones", tags=["Mediciones"])
water_service = WaterQualityService()

@router.post("/", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_measurement(payload: ESP32Payload, request: Request):
    try:
        return water_service.register_reading(payload=payload, endpoint=str(request.url.path))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error interno: {str(e)}")

@router.get("/latest")
def get_latest_measurement():
    return water_service.get_latest()

@router.get("/filtrar")
def filter_measurements(
    fecha: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD"),
    hora: Optional[int] = Query(None, description="Hora de 0 a 23"),
    limit: int = Query(1, ge=1, le=50, description="Cantidad máxima de registros")
):
    try:
        data = water_service.filtrar(fecha=fecha, hora=hora, limit=limit)
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron registros.")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al filtrar: {str(e)}")
