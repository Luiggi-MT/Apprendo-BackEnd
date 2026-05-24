import os
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
from dotenv import load_dotenv

load_dotenv()


class MongoDB:
    def __init__(self):
        try:
            mongo_host = os.getenv('MONGO_HOST', 'localhost')
            running_in_docker = os.path.exists('/.dockerenv')

            # Si se ejecuta en local y el host apunta al nombre interno de Docker,
            # usamos localhost para poder conectar al puerto publicado (27017).
            if not running_in_docker and mongo_host == 'mongo':
                mongo_host = 'localhost'

            uri = (
                f"mongodb://"
                f"{os.getenv('MONGO_USERNAME')}:"
                f"{os.getenv('MONGO_PASSWORD')}@"
                f"{mongo_host}:"
                f"{os.getenv('MONGO_PORT')}/"
            )

            self.client = MongoClient(uri)

            self.db = self.client[
                os.getenv("MONGO_DB")
            ]

        except Exception as err:
            raise Exception(
                f"Error conectando a MongoDB: {err}"
            )

    def get_db(self):
        return self.db

    def get_collection(self, name):
        return self.db[name]

    def close(self):
        self.client.close()
