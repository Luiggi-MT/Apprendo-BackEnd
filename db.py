import os
import time
import pymysql
from pymysql.cursors import DictCursor
# Necesitarás instalar: pip install DBUtils
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        # Se inicializa en la primera consulta para no romper el arranque de Flask si la BD aun no esta lista.
        self.pool = None
        self.pool_config = {
            'creator': pymysql,
            'maxconnections': 10,
            'mincached': 1,
            'maxcached': 5,
            'blocking': True,
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
        }

    def _ensure_pool(self):
        if self.pool is not None:
            return

        attempts = int(os.getenv('DB_CONNECT_RETRIES', '10'))
        delay = float(os.getenv('DB_CONNECT_RETRY_DELAY', '1'))
        last_error = None

        for _ in range(attempts):
            try:
                self.pool = PooledDB(**self.pool_config)
                return
            except Exception as err:
                last_error = err
                time.sleep(delay)

        raise Exception(
            "No se pudo inicializar el pool de BD tras "
            f"{attempts} intentos. Error: {last_error}"
        )

    def connect(self):
        try:
            self._ensure_pool()
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
