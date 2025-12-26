from flask import Blueprint, request
from werkzeug.security import generate_password_hash
from db import Database
from const import LIMIT
import os

db = Database()
UPLOAD_FOLDER = os.getenv('FILE_PATH')

students = Blueprint('students', __name__)

@students.route('/students')
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
        query = """
            SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz, id
            FROM estudiantes
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, offset))
        students = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM estudiantes")
        count = cursor.fetchone()
        total_count = count[0] if isinstance(count, tuple) else list(count.values())[0]

        student_list = []
        for student in students:
            accesibilidad = student['accesibilidad'].split(',') if student['accesibilidad'] else []
            student_list.append({
                'foto': student['foto'],
                'username': student['username'],
                'tipoContraseña': student['tipoContraseña'],
                'accesibilidad': accesibilidad,
                'preferenciasVisualizacion': student['preferenciasVisualizacion'],
                'asistenteVoz': student['asistenteVoz'],
                'id': student['id']
            })

        return {
            'students': student_list,
            'offset': offset + limit,
            'count': total_count
        }, 200

    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route('/student/<string:username>', methods=['DELETE'])
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

@students.route('/students/<string:username>')
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
        
        students_list = []
        for student in students:
            accesibilidad = student['accesibilidad'].split(',') if student['accesibilidad'] else []
            students_list.append({
                'foto': student['foto'],
                'username': student['username'],
                'tipoContraseña': student['tipoContraseña'],
                'accesibilidad': accesibilidad,
                'preferenciasVisualizacion': student['preferenciasVisualizacion'],
                'asistenteVoz': student['asistenteVoz']
            })
        return {'students': students_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route('/student', methods=['POST'])
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

@students.route('/student/<string:username>/photo', methods=['POST'])
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

@students.route('/student/<int:id>', methods=['PUT'])
def update_student(id):
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    try:
        fields = []
        params = [] 

        data = request.get_json()

        
        
        if data.get('username'):
            fields.append("username = %s")
            params.append(data.get('username'))
        
        if data.get('contraseña'): 
            fields.append("contraseña = %s")
            params.append(generate_password_hash(data.get('contraseña'), method='pbkdf2:sha256', salt_length=16))
        
        if data.get('tipoContraseña'):
            fields.append("tipoContraseña = %s")
            params.append(data.get('tipoContraseña'))

        accesibilidad = data.get('accesibilidad')
        if isinstance(accesibilidad, list):
            accesibilidad_str = ','.join(accesibilidad)
            fields.append("accesibilidad = %s")
            params.append(','.join(accesibilidad))
        
        if data.get('tipoContraseña'):
            fields.append("tipoContraseña = %s")
            params.append(data.get('tipoContraseña'))

        if data.get('preferenciasVisualizacion'):
            fields.append("preferenciasVisualizacion = %s")
            params.append(data.get('preferenciasVisualizacion'))
        
        if data.get('asistenteVoz'):
            fields.append("asistenteVoz = %s")
            params.append(data.get('asistenteVoz'))
        
        if not fields:
            return {'error': 'No fields to update'}, 400
        query = f"UPDATE estudiantes SET {', '.join(fields)} WHERE id = %s"
        params.append(id)

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