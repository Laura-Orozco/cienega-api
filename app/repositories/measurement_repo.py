import psycopg2.extras
from app.database import DatabaseManager

class MeasurementRepository:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def get_device_by_identifier(self, identifier: str):
        query = "SELECT id_dispositivo FROM dispositivos WHERE identificador = %s;"
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (identifier,))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self.db_manager.release_connection(conn)

    def get_sensor_by_device(self, id_dispositivo: int):
        query = "SELECT id_sensor FROM sensores WHERE id_dispositivo = %s LIMIT 1;"
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (id_dispositivo,))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self.db_manager.release_connection(conn)

    def insert_measurement(self, id_sensor: int, id_estado: int, temp: float, turb: float):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO mediciones (id_sensor, id_estado) VALUES (%s, %s) RETURNING id_medicion, fecha_hora;",
                    (id_sensor, id_estado)
                )
                id_medicion, fecha_hora = cur.fetchone()

                cur.execute(
                    "INSERT INTO valores_medicion (id_medicion, id_parametro, valor, unidad) VALUES (%s, %s, %s, %s);",
                    (id_medicion, 1, temp, "°C")
                )
                cur.execute(
                    "INSERT INTO valores_medicion (id_medicion, id_parametro, valor, unidad) VALUES (%s, %s, %s, %s);",
                    (id_medicion, 2, turb, "NTU")
                )

                conn.commit()
                return id_medicion, fecha_hora
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.db_manager.release_connection(conn)

    def log_api_call(self, id_dispositivo: int, id_medicion: int, metodo: str, endpoint: str, status_code: int):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO registros_api (id_dispositivo, id_medicion, metodo, endpoint, codigo_http, estado_envio)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (id_dispositivo, id_medicion, metodo, endpoint, status_code, "EXITOSO")
                )
                conn.commit()
        finally:
            self.db_manager.release_connection(conn)

    def get_latest_measurement(self):
        query = """
            SELECT m.id_medicion, m.fecha_hora, ec.nombre AS estado,
                   MAX(CASE WHEN p.nombre ILIKE '%temperatura%' THEN vm.valor END) AS temperatura,
                   MAX(CASE WHEN p.nombre ILIKE '%turbidez%' THEN vm.valor END) AS turbidez,
                   u.lugar, u.ubicabilidad
            FROM mediciones m
            LEFT JOIN estados_calidad ec ON m.id_estado = ec.id_estado
            JOIN sensores s ON m.id_sensor = s.id_sensor
            JOIN ubicaciones u ON s.id_ubicacion = u.id_ubicacion
            JOIN valores_medicion vm ON m.id_medicion = vm.id_medicion
            JOIN parametros p ON vm.id_parametro = p.id_parametro
            GROUP BY m.id_medicion, m.fecha_hora, ec.nombre, u.lugar, u.ubicabilidad
            ORDER BY m.fecha_hora DESC
            LIMIT 1;
        """
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id_medicion": row[0],
                    "fecha_hora": row[1],
                    "estado": row[2],
                    "temperatura": float(row[3]) if row[3] is not None else None,
                    "turbidez": float(row[4]) if row[4] is not None else None,
                    "lugar": row[5],
                    "ubicabilidad": row[6]
                }
        finally:
            self.db_manager.release_connection(conn)

    def filter_measurements(self, fecha=None, hora=None, limit=1):
        conn = self.db_manager.get_connection()
        try:
            # Usar RealDictCursor para evitar desbordes de índices en tuplas
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                where_clauses = ["1=1"]
                params = []

                if fecha:
                    where_clauses.append("DATE(m.fecha_hora) = %s")
                    params.append(fecha)

                if hora is not None:
                    where_clauses.append("EXTRACT(HOUR FROM m.fecha_hora) = %s")
                    params.append(int(hora))

                where_sql = " AND ".join(where_clauses)

                query = f"""
                    SELECT m.id_medicion, m.fecha_hora, 
                           COALESCE(ec.nombre, 'Sin clasificar') AS estado,
                           MAX(CASE WHEN p.nombre ILIKE '%temperatura%' THEN vm.valor END) AS temperatura,
                           MAX(CASE WHEN p.nombre ILIKE '%turbidez%' THEN vm.valor END) AS turbidez,
                           COALESCE(u.lugar, '') AS lugar, 
                           COALESCE(u.ubicabilidad, '') AS ubicabilidad
                    FROM mediciones m
                    LEFT JOIN estados_calidad ec ON m.id_estado = ec.id_estado
                    LEFT JOIN sensores s ON m.id_sensor = s.id_sensor
                    LEFT JOIN ubicaciones u ON s.id_ubicacion = u.id_ubicacion
                    LEFT JOIN valores_medicion vm ON m.id_medicion = vm.id_medicion
                    LEFT JOIN parametros p ON vm.id_parametro = p.id_parametro
                    WHERE {where_sql}
                    GROUP BY m.id_medicion, m.fecha_hora, ec.nombre, u.lugar, u.ubicabilidad
                    ORDER BY m.fecha_hora DESC
                    LIMIT %s;
                """
                params.append(int(limit))

                cur.execute(query, tuple(params))
                rows = cur.fetchall()

                resultados = []
                for r in rows:
                    resultados.append({
                        "id_medicion": r.get("id_medicion"),
                        "fecha_hora": str(r.get("fecha_hora")),
                        "estado": r.get("estado"),
                        "temperatura": float(r["temperatura"]) if r.get("temperatura") is not None else None,
                        "turbidez": float(r["turbidez"]) if r.get("turbidez") is not None else None,
                        "lugar": r.get("lugar"),
                        "ubicabilidad": r.get("ubicabilidad")
                    })
                return resultados
        finally:
            self.db_manager.release_connection(conn)
