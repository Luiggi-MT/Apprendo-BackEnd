import os
import MySQLdb as mysql

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.user =  os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')

    def connect(self):
        try:
            connection = mysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return connection
        except mysql.Error as err:
            raise Exception(f"Fallo al conectar a la base de datos. Error: {err}")