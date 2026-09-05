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

    def filter_measurements(self, fecha=None, hora=None, limit=10):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                condiciones = []
                valores = []

                if fecha:
                    condiciones.append("TO_CHAR(m.fecha_hora, 'YYYY-MM-DD') = %s")
                    valores.append(str(fecha).strip())

                if hora is not None:
                    condiciones.append("EXTRACT(HOUR FROM m.fecha_hora) = %s")
                    valores.append(int(hora))

                where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
                limite_num = max(1, min(int(limit), 50))

                # Nota los dobles '%%' para evitar que psycopg2 intente sustituirlos como parámetros de tupla
                query = f"""
                    SELECT m.id_medicion, m.fecha_hora, ec.nombre AS estado,
                           MAX(CASE WHEN p.nombre ILIKE '%%temperatura%%' THEN vm.valor END) AS temperatura,
                           MAX(CASE WHEN p.nombre ILIKE '%%turbidez%%' THEN vm.valor END) AS turbidez,
                           u.lugar, u.ubicabilidad
                    FROM mediciones m
                    LEFT JOIN estados_calidad ec ON m.id_estado = ec.id_estado
                    JOIN sensores s ON m.id_sensor = s.id_sensor
                    JOIN ubicaciones u ON s.id_ubicacion = u.id_ubicacion
                    JOIN valores_medicion vm ON m.id_medicion = vm.id_medicion
                    JOIN parametros p ON vm.id_parametro = p.id_parametro
                    {where_sql}
                    GROUP BY m.id_medicion, m.fecha_hora, ec.nombre, u.lugar, u.ubicabilidad
                    ORDER BY m.fecha_hora DESC
                    LIMIT {limite_num};
                """

                if valores:
                    cur.execute(query, tuple(valores))
                else:
                    cur.execute(query)

                filas = cur.fetchall()

                if not filas:
                    return []

                resultados = []
                for fila in filas:
                    resultados.append({
                        "id_medicion": fila[0],
                        "fecha_hora": str(fila[1]),
                        "estado": fila[2] if fila[2] else "Sin estado",
                        "temperatura": float(fila[3]) if fila[3] is not None else None,
                        "turbidez": float(fila[4]) if fila[4] is not None else None,
                        "lugar": fila[5],
                        "ubicabilidad": fila[6]
                    })
                return resultados
        finally:
            self.db_manager.release_connection(conn)
