import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class MongoDB:
    def __init__(self):
        try:
            uri = (
                f"mongodb://"
                f"{os.getenv('MONGO_USERNAME')}:"
                f"{os.getenv('MONGO_PASSWORD')}@"
                f"{os.getenv('MONGO_HOST')}:"
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
