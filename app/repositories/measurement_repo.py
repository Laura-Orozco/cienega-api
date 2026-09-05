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
            with conn.cursor() as cur:
                clauses = []
                params = []

                if fecha:
                    clauses.append("DATE(m.fecha_hora) = %s")
                    params.append(str(fecha))

                if hora is not None:
                    clauses.append("EXTRACT(HOUR FROM m.fecha_hora) = %s")
                    params.append(int(hora))

                where_stmt = ("WHERE " + " AND ".join(clauses)) if clauses else ""
                limite = max(1, min(int(limit), 50))

                query = f"""
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
                    {where_stmt}
                    GROUP BY m.id_medicion, m.fecha_hora, ec.nombre, u.lugar, u.ubicabilidad
                    ORDER BY m.fecha_hora DESC
                    LIMIT {limite};
                """

                if params:
                    cur.execute(query, tuple(params))
                else:
                    cur.execute(query)

                rows = cur.fetchall()

                resultados = []
                for row in rows:
                    if not row:
                        continue
                    resultados.append({
                        "id_medicion": row[0],
                        "fecha_hora": str(row[1]),
                        "estado": row[2] if len(row) > 2 and row[2] is not None else "Sin estado",
                        "temperatura": float(row[3]) if len(row) > 3 and row[3] is not None else None,
                        "turbidez": float(row[4]) if len(row) > 4 and row[4] is not None else None,
                        "lugar": row[5] if len(row) > 5 else None,
                        "ubicabilidad": row[6] if len(row) > 6 else None
                    })
                return resultados
        finally:
            self.db_manager.release_connection(conn)
