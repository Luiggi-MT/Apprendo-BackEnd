from flask import Blueprint, send_file, abort, request, session
from werkzeug.security import check_password_hash, generate_password_hash


from db import Database
import os
import glob
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
        limit = int(request.args.get('limit', LIMIT))
        if limit <= 0: 
            limit = LIMIT
    except (ValueError, TypeError): 
        limit = LIMIT
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz, id from estudiantes LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))
        students = cursor.fetchall()

        query = "SELECT COUNT(*) from estudiantes"
        cursor.execute(query)
        count = cursor.fetchone()

        cursor.close()
        conn.close()
        student_list = []
        for student in students:
            accesibilidad = student[3].split(',') if student[4] else []
            student_list.append({
                'foto': student[0],
                'username': student[1],
                'tipoContraseña': student[2],
                'accesibilidad': accesibilidad,
                'preferenciasVisualizacion': student[4],
                'asistenteVoz': student[5],
                'id': student[6]
            })
        return {'students': student_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}
    

@routes.route('/student/<string:username>', methods=['DELETE'])
def delete_student(username): 
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        """HAY que añadir comprobación de que no tenga actividades asigandas y por hacer"""
        query = "DELETE FROM estudiantes WHERE username = %s"
        cursor.execute(query, (username, ))

        conn.commit() #Guarda los cambios en la base de datos

        if cursor.rowcount == 0: 
            return {"Error" : "Student not found"}, 404
        
        return {"message" : "Deleted Student succesful"}, 200
    except Exception as e: 
        if conn: 
            conn.rollback() # Si algo ha fallado, deshacemos el cambio 
        return {"Error" : str(e)}, 500
    finally: 
        if conn: 
            cursor.close()
            conn.close()

@routes.route('/students/<string:username>')
def get_student(username):
    try:
        try: 
            offset = int(request.args.get('offset', 0))
            if offset < 0:
                offset = 0
        except ValueError:
            offset = 0
        try:
            limit = int(request.args.get('limit', LIMIT))
            if limit <= 0: 
                limit = LIMIT
        except (ValueError, TypeError): 
            limit = LIMIT
        conn = db.connect()
        cursor = conn.cursor()
        username_pattern = f"%{username}%"
        query = "SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz FROM estudiantes WHERE username LIKE %s ORDER BY username LIMIT %s OFFSET %s"
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
            accesibilidad = student[4].split(',') if student[4] else []
            students_list.append({
                'foto': student[0],
                'username': student[1],
                'tipoContraseña': student[2],
                'accesibilidad': accesibilidad,
                'preferenciasVisualizacion': student[4],
                'asistenteVoz': student[5]
            })
        return {'students': students_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}
    
@routes.route('/student', methods=['POST'])
def create_student():
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    try:
        data = request.get_json()
        
        username = data.get('username')
        contraseña = data.get('contraseña')
        tipoContraseña = data.get('tipoContraseña')
        accesibilidad = data.get('accesibilidad')
        preferenciasVisualizacion = data.get('preferenciasVisualizacion')
        asistenteVoz = data.get('asistenteVoz')

        hashed_contraseña = generate_password_hash(contraseña, method='pbkdf2:sha256', salt_length=16)
        accesibilidad_str = ','.join(accesibilidad) if isinstance(accesibilidad, list) else ''

        conn = db.connect()
        cursor = conn.cursor()
        query = """INSERT INTO estudiantes (username, contraseña, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (username, hashed_contraseña, tipoContraseña, accesibilidad_str, preferenciasVisualizacion, asistenteVoz))
        conn.commit()

        return {'message': 'Student created successfully'}, 201
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@routes.route('/student/<string:username>/photo', methods=['POST'])
def upload_student_photo(username):
    try:
        conn = db.connect()
        cursor = conn.cursor()

        if 'photo' not in request.files:
            return {'error': 'No photo uploaded'}, 400

        photo = request.files['photo']
        if photo.filename == '':
            return {'error': 'No photo selected'}, 400


        student_dir = os.path.join(UPLOAD_FOLDER, username)
        if not os.path.exists(student_dir):
            os.makedirs(student_dir) # Crear el directorio si no existe
        
        ext = os.path.splitext(photo.filename)[1].lower() # Obtener la extensión del archivo
        foto_perfil = f"fotoPerfil{ext}"
        file_path = os.path.join(student_dir, foto_perfil)

        foto_perfil_anterior = glob.glob(os.path.join(student_dir, "fotoPerfil.*"))
        for archivo in foto_perfil_anterior:
            try: 
                os.remove(archivo)
            except Exception as e:
                pass

        photo.save(file_path)

        db_path = f"{username}/{foto_perfil}"

        query = "UPDATE estudiantes SET foto = %s WHERE username = %s"
        cursor.execute(query, (db_path, username))
        conn.commit()

        return {'message': 'Photo uploaded successfully'}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@routes.route('/student/<int:id>', methods=['PUT'])
def update_student(id):
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    try:
        data = request.get_json()
        contraseña = data.get('contraseña')
        tipoContraseña = data.get('tipoContraseña')
        accesibilidad = data.get('accesibilidad')
        preferenciasVisualizacion = data.get('preferenciasVisualizacion')
        asistenteVoz = data.get('asistenteVoz')
        username = data.get('username')

        accesibilidad_str = ','.join(accesibilidad) if isinstance(accesibilidad, list) else ''

        query = ""
        params = ()
        if contraseña and contraseña.strip() != "":
            hashed_constraseña = generate_password_hash(contraseña, method='pbkdf2:sha256', salt_length=16)
            query = """UPDATE estudiantes
                          SET contraseña = %s, username = %s, tipoContraseña = %s, accesibilidad = %s,
                                preferenciasVisualizacion = %s, asistenteVoz = %s
                          WHERE id = %s"""
            params = (hashed_constraseña, username, tipoContraseña, accesibilidad_str, preferenciasVisualizacion, asistenteVoz, id)
        else:
            query = """UPDATE estudiantes 
                       SET username = %s, tipoContraseña = %s, accesibilidad = %s, 
                           preferenciasVisualizacion = %s, asistenteVoz = %s 
                       WHERE id = %s"""
            params = (username, tipoContraseña, accesibilidad_str, preferenciasVisualizacion, asistenteVoz, id)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return {'error': 'Student not found'}, 404

        return {'message': 'Student updated successfully'}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

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
        return {'ok': False, 'message': 'No active session'}, 401


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

