import os
import pymysql
from dotenv import load_dotenv
load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.user =  os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')

    def connect(self):
        try:
            connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4', 
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except pymysql.Error as err:
            raise Exception(f"Fallo al conectar a la base de datos. Error: {err}")