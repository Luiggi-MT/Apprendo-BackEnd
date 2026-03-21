import os
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB # Necesitarás instalar: pip install DBUtils
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        # Configuramos el pool al instanciar la clase
        #Reutilizamos conexiones en lugar de crear una nueva cada vez, lo que mejora el rendimiento y evita errores 500 por saturación
        self.pool = PooledDB(
            creator=pymysql,  # El módulo que usamos
            maxconnections=10, # Conexiones máximas totales
            mincached=2,       # Conexiones mínimas siempre abiertas
            maxcached=5,       # Conexiones máximas inactivas en espera
            blocking=True,     # Esperar si el pool está lleno (evita errores 500)
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
            raise Exception(f"Fallo al obtener conexión del pool. Error: {err}")