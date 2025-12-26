from flask import Blueprint
from db import Database

db = Database()


estados = Blueprint('status', __name__)

@estados.route('/')
def hello_world():
    return '<h1>Hello, World!</h1>'

@estados.route('/status')
def status():
    try:
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT 1")

        return '<h1>Database Connection Status: OK</h1>'
    except Exception as e:
        return f'<h1>Database Connection Error: {e}</h1>'
    finally:
        if conn:
            cursor.close()
            conn.close()