from flask import Blueprint, request, jsonify
from exponent_server_sdk import PushClient, PushMessage

from db import Database 

# Instanciamos la base de datos como haces en tareas.py
db = Database()

notificaciones = Blueprint('notificaciones', __name__)

# La función enviar_push debe estar aquí para que otros la importen
def enviar_push(token, titulo, mensaje):
    if not token or not token.startswith("ExponentPushToken"):
        return False
    try:
        PushClient().publish(
            PushMessage(to=token, title=titulo, body=mensaje)
        )
        return True
    except Exception as e:
        print(f"Error enviando push: {e}")
        return False

@notificaciones.route('/guardar-token', methods=['POST'])
def guardar_token():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        id_estudiante = data.get('id_estudiante')
        token = data.get('token')

        conn = db.connect()
        cursor = conn.cursor()
        
        query = "UPDATE estudiantes SET expo_push_token = %s WHERE id = %s"
        cursor.execute(query, (token, id_estudiante))
        conn.commit()

        return jsonify({"message": "Token guardado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@notificaciones.route('/guardar-token-profesor', methods=['POST'])
def guardar_token_profesor():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        id_profesor = data.get('id_profesor')
        token = data.get('token')

        conn = db.connect()
        cursor = conn.cursor()
        
        query = "UPDATE profesores SET expo_push_token = %s WHERE id = %s"
        cursor.execute(query, (token, id_profesor))
        conn.commit()

        return jsonify({"message": "Token guardado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()