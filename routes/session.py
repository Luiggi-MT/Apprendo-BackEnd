from flask import Blueprint, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from db import Database


db = Database()
auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['POST'])
def login(): 
    if not request.is_json: 
        return {'error': 'Missing JSON in request'}, 400
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        query = "SELECT password, foto, tipo FROM profesores WHERE username = %s"
        cursor.execute(query, (username,))
        profesor = cursor.fetchone()

        if profesor : 
            store_hash = profesor['password']
            if(check_password_hash(store_hash, password)):
                session['logged_in'] = True
                session['username'] = username
                session['foto'] = profesor['foto']
                session['tipo'] = profesor['tipo']
                return {'username': username, 'foto': profesor['foto'], 'tipo': profesor['tipo']}, 200
            else:
                return {'error': 'Invalid credentials'}, 401
        else:
            return {'error': 'Invalid credentials'}, 401

    except Exception as e:
        return {'error': str(e)}, 500
    finally: 
        if conn:
            cursor.close()
            conn.close()


@auth.route('/logout', methods=['POST'])
def logout():
    try: 
        session.clear()
        return {'message': 'Logout succesful'}, 200
    except Exception as e: 
        return {'error': 'Failed to log out'}, 500

@auth.route('/session')
def get_session(): 
    if session.get('logged_in'): 
        return {
            'ok' : True,
            'username': session.get('username'), 
            'foto': session.get('foto'), 
            'tipo': session.get('tipo')
        }, 200
    else: 
        return {'ok': False, 'message': 'No active session'}, 401