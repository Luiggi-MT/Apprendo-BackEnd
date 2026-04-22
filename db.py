import os
import pymysql
from pymysql.cursors import DictCursor
# Necesitarás instalar: pip install DBUtils
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        # Configuramos el pool al instanciar la clase
        # Reutilizamos conexiones en lugar de crear una nueva cada vez, lo que mejora el rendimiento y evita errores 500 por saturación
        self.pool = PooledDB(
            creator=pymysql,  # El módulo que usamos
            maxconnections=10,  # Conexiones máximas totales
            mincached=2,       # Conexiones mínimas siempre abiertas
            maxcached=5,       # Conexiones máximas inactivas en espera
            # Esperar si el pool está lleno (evita errores 500)
            blocking=True,
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset='utf8mb4',
            cursorclass=DictCursor
        )

    def connect(self):
        try:
            # En lugar de pymysql.connect, pedimos una conexión al pool
            return self.pool.connection()
        except Exception as err:
            raise Exception(
                f"Fallo al obtener conexión del pool. Error: {err}")

    def close(self, connection):
        try:
            connection.close()  # Esto devuelve la conexión al pool, no la cierra realmente
        except Exception as err:
            raise Exception(f"Fallo al cerrar conexión. Error: {err}")

    def fetch_query(self, query, params=None, fetchone=False):
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchone() if fetchone else cursor.fetchall()
                cursor.close()
                return result
        except Exception as err:
            raise Exception(f"Fallo al ejecutar consulta. Error: {err}")
        finally:
            self.close(connection)

    def execute_query(self, query, params=None):
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                affected_rows = cursor.rowcount
                connection.commit()
                return affected_rows
        except Exception as err:
            connection.rollback()
            raise Exception(
                f"Fallo al ejecutar y confirmar la consulta. Error: {err}")
        finally:
            self.close(connection)
