from flask import Blueprint, send_file, abort, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import Database
import os
from const import LIMIT 

routes = Blueprint('routes', __name__)
db = Database()

UPLOAD_FOLDER = os.getenv('FILE_PATH')
FOLDER_COMPONENTS = os.getenv('FILE_COMPONENTS')

@routes.route('/')
def hello_world():
    return '<h1>Hello, World!</h1>'

@routes.route('/status')
def status():
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return '<h1>Database Connection Status: OK</h1>'
    except Exception as e:
        return f'<h1>Database Connection Error: {e}</h1>'
    
@routes.route('/admins')
def get_admins():
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM admins")
        admins = cursor.fetchall()
        cursor.close()
        conn.close()
        return {'admins': admins}
    except Exception as e:
        return {'error': str(e)}
    
@routes.route('/students')
def get_students():
    try:
        offset = int(request.args.get('offset', 0))
        if offset < 0:
            offset = 0
    except ValueError:
        offset = 0
    try:
        limit = LIMIT
        conn = db.connect()
        cursor = conn.cursor()
        query = "SELECT foto, username from estudiantes LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))
        students = cursor.fetchall()

        query = "SELECT COUNT(*) from estudiantes"
        cursor.execute(query)
        count = cursor.fetchone()

        cursor.close()
        conn.close()
        student_list = []
        for student in students:
            student_list.append({
                'foto': student[0],
                'username': student[1]
            })
        return {'students': student_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}
    
@routes.route('/students/<string:username>')
def get_student(username):
    try:
        try: 
            offset = int(request.args.get('offset', 0))
            if offset < 0:
                offset = 0
        except ValueError:
            offset = 0
        limit = LIMIT
        conn = db.connect()
        cursor = conn.cursor()
        username_pattern = f"%{username}%"
        query = "SELECT foto, username FROM estudiantes WHERE username LIKE %s ORDER BY username LIMIT %s OFFSET %s"
        cursor.execute(query, (username_pattern, limit, offset))
        students = cursor.fetchall()
        query = "SELECT COUNT(*) FROM estudiantes WHERE username LIKE %s"
        cursor.execute(query, (username_pattern,))
        count = cursor.fetchone()
        cursor.close()
        conn.close()
        print("count: ",count)
        students_list = []
        for student in students:
            students_list.append({
                'foto': student[0],
                'username': student[1]
            })
        return {'students': students_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}

@routes.route('/foto/<path:filename>')
def get_foto(filename): 
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        """ Hay que arreglar esta parte 
            if not file_path.startswith(os.path.abspath(UPLOAD_FOLDER)):
            abort(404)
        """
        return send_file(file_path)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return {'error': str(e)}    
    
@routes.route('/component/<path:filename>')
def get_component(filename): 
    try: 
        file_path = os.path.join(FOLDER_COMPONENTS, filename)
        return send_file(file_path)
    except FileExistsError: 
        abort(404)
    except Exception as e: 
        return {'error': str(e)}
    
@routes.route('/login', methods=['POST'])
def login(): 
    print("Entra")
    if not request.is_json: 
        return {'error': 'Missing JSON in request'}, 400
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        print(username)
        print(password)

        query = "SELECT password, foto, tipo FROM profesores WHERE username = %s"
        cursor.execute(query, (username,))
        profesor = cursor.fetchone()

        cursor.close()
        conn.close()

        if profesor : 
            store_hash = profesor[0]
            if(check_password_hash(store_hash, password)):
                session['logged_in'] = True
                session['username'] = username
                session['foto'] = profesor[1]
                session['tipo'] = profesor[2]
                return {'username': username, 'foto': profesor[1], 'tipo': profesor[2]}, 200
            else:
                return {'error': 'Invalid credentials'}, 401
        else:
            return {'error': 'Invalid credentials'}, 401

    except Exception as e:
        return {'error': str(e)}, 500


@routes.route('/logout', methods=['POST'])
def logout():
    try: 
        session.clear()
        return {'message': 'Logout succesful'}, 200
    except Exception as e: 
        return {'error': 'Failed to log out'}, 500
    
@routes.route('/session')
def get_session(): 
    if session.get('logged_in'): 
        return {
            'ok' : True,
            'username': session.get('username'), 
            'foto': session.get('foto'), 
            'tipo': session.get('tipo')
        }, 200
    else: 
        return {'ok': False, 'message': 'No active session'}


@routes.route('/add_admin_test', methods=['POST'])
def add_admin_test():
    
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {'error': 'Missing username or password'}, 400

    try:
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        conn = db.connect()
        cursor = conn.cursor()
        
        check_query = "SELECT username FROM admins WHERE username = %s"
        cursor.execute(check_query, (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {'error': f'Admin "{username}" already exists'}, 409

        insert_query = "INSERT INTO admins (username, password) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, hashed_password))
        
        conn.commit()
        cursor.close()
        conn.close()

        return {'message': 'Test Admin registered successfully with hashed password'}, 201

    except Exception as e:
        return {'error': str(e)}, 500

