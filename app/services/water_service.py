from app.repositories.measurement_repo import MeasurementRepository
from app.schemas.measurement import ESP32Payload

class WaterQualityService:
    def __init__(self):
        self.repo = MeasurementRepository()

    def evaluate_quality(self, turbidez: float, temperatura: float) -> tuple[int, str]:
        if turbidez < 5.0 and (15.0 <= temperatura <= 25.0):
            return 1, "Excelente"
        elif turbidez < 15.0 and temperatura <= 30.0:
            return 2, "Aceptable"
        else:
            return 3, "No Apta"

    def register_reading(self, payload: ESP32Payload, endpoint: str):
        id_disp = self.repo.get_device_by_identifier(payload.identificador)
        if not id_disp:
            raise ValueError(f"El dispositivo '{payload.identificador}' no existe en la base de datos.")

        id_sensor = self.repo.get_sensor_by_device(id_disp)
        if not id_sensor:
            raise ValueError("No se encontró ningún sensor asignado a este dispositivo.")

        id_estado, estado_nombre = self.evaluate_quality(payload.turbidez, payload.temperatura)

        id_medicion, fecha_hora = self.repo.insert_measurement(
            id_sensor=id_sensor,
            id_estado=id_estado,
            temp=payload.temperatura,
            turb=payload.turbidez
        )

        self.repo.log_api_call(
            id_dispositivo=id_disp,
            id_medicion=id_medicion,
            metodo="POST",
            endpoint=endpoint,
            status_code=201
        )

        return {
            "id_medicion": id_medicion,
            "estado_calidad": estado_nombre,
            "mensaje": "Medición registrada satisfactoriamente",
            "fecha_hora": fecha_hora
        }

    def get_latest(self):
        data = self.repo.get_latest_measurement()
        if not data:
            return {"mensaje": "No hay lecturas registradas aún."}
        return data

    def filtrar(self, fecha=None, hora=None, limit=1):
        return self.repo.filter_measurements(fecha=fecha, hora=hora, limit=limit)
