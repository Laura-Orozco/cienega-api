from fastapi import APIRouter, HTTPException, Request, status
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

def filter_measurements(self, fecha=None, hora=None, limit=1):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                # Construcción dinámica de la consulta SQL
                query = "SELECT id, temperatura, turbidez, estado, fecha_hora, lugar, ubicabilidad FROM mediciones WHERE 1=1"
                params = []

                if fecha:
                    query += " AND DATE(fecha_hora) = %s"
                    params.append(fecha)

                if hora is not None:
                    query += " AND EXTRACT(HOUR FROM fecha_hora) = %s"
                    params.append(hora)

                query += " ORDER BY fecha_hora DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, tuple(params))
                rows = cur.fetchall()

                resultados = []
                for row in rows:
                    resultados.append({
                        "id": row[0],
                        "temperatura": row[1],
                        "turbidez": row[2],
                        "estado": row[3],
                        "fecha_hora": str(row[4]),
                        "lugar": row[5],
                        "ubicabilidad": row[6]
                    })
                return resultados
        finally:
            self.db_manager.release_connection(conn)
