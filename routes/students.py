from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from db import Database
from const import LIMIT

import random
import os
import glob
import shutil

db = Database()
UPLOAD_FOLDER = os.getenv('FILE_PATH')

students = Blueprint('students', __name__)

@students.route('/students')
def get_students():
    conn = None
    cursor = None
    try:
        offset = int(request.args.get('offset', 0))
        if offset <= 0:
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
                'id': student['id'], 
                
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
@jwt_required()
def delete_student(username): 
    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"Error": "Acceso denegado. Solo los administradores pueden eliminar estudiantes."}, 403
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        
        # 1. Obtener el id del estudiante
        query = "SELECT id FROM estudiantes WHERE username = %s"
        cursor.execute(query, (username, ))
        student = cursor.fetchone()
        
        if not student: 
            return {"Error": "Student not found"}, 404
            
        student_id = student['id']

        # 2. Borrar registros de la base de datos
        query = "DELETE FROM estudiantes WHERE username = %s"
        cursor.execute(query, (username, ))
        conn.commit()

        # 3. Borramos el directorio físico y manejamos la respuesta
        if cursor.rowcount > 0: 
            student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(student_id))
            
            if os.path.exists(student_dir): 
                try: 
                    shutil.rmtree(student_dir)
                except Exception as dir_error:
                    print(f"Error borrando directorio: {dir_error}"), 500
            
            # RETORNO SIEMPRE que se haya borrado de la DB
            return {"message": "Estudiante eliminado correctamente"}, 200
        
        # RETORNO si por alguna razón rowcount fue 0 tras el commit
        return {"Error": "No se ha podido eliminar al estudiante"}, 400

    except Exception as e: 
        if conn: 
            conn.rollback() 
        return {"Error": str(e)}, 500
    finally: 
        if conn: 
            cursor.close()
            conn.close()

@students.route('/students/<string:username>')
def get_student(username):
    conn = None
    cursor = None
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
                'asistenteVoz': student['asistenteVoz'], 
            })
        return {'students': students_list, 'offset': offset + limit, 'count': count}
    except Exception as e:
        return {'error': str(e)}
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route('/student', methods=['POST'])
@jwt_required()
def create_student():
    claims = get_jwt()
    print(claims)
    if claims.get('tipo') != 'admin':
        return {'error': 'Acceso denegado. Solo los administradores pueden crear estudiantes.'}, 403
    conn = None
    cursor = None
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    try:
        data = request.get_json()
        fields = ['username', 'tipoContraseña', 'preferenciasVisualizacion', 'asistenteVoz']
        params = [
            data.get('username'),
            data.get('tipoContraseña'),
            data.get('preferenciasVisualizacion'),
            data.get('asistenteVoz'),
        ]
        
        if data.get('contraseña'): 
            
            contraseña = data.get('contraseña')
            hashed_contraseña = generate_password_hash(contraseña, method='pbkdf2:sha256', salt_length=16)
            params.append(hashed_contraseña)
            fields.append('contraseña')
        
        if data.get('accesibilidad'): 
            accesibilidad = data.get('accesibilidad')
            # IMPORTANTE: Para un SET de MySQL, las opciones van unidas por coma SIN espacios
            if isinstance(accesibilidad, list):
                accesibilidad_str = ','.join([a.strip() for a in accesibilidad])
            else:
                accesibilidad_str = accesibilidad.strip()
            
            fields.append('accesibilidad')
            params.append(accesibilidad_str)


        placeholders = ",".join(["%s"] * len(fields))
        nombre_columnas = ", ".join(fields)

        query = f"INSERT INTO estudiantes ({nombre_columnas}) VALUES ({placeholders})"
        
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        id_estudiante = cursor.lastrowid
        conn.commit()

        return {
            'message': 'Estudiante creado correctamente', 
            'id': id_estudiante,
            'ok': True
        }, 201

    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        # Cierre seguro de recursos
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@students.route('/student/<int:id>/photo', methods=['POST'])
def upload_student_photo(id):
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        if 'photo' not in request.files:
            return {'error': 'No photo uploaded'}, 400

        photo = request.files['photo']
        if photo.filename == '':
            return {'error': 'No photo selected'}, 400

        query = """SELECT foto FROM estudiantes WHERE id = %s"""
        cursor.execute(query, (id,))
        foto_url = cursor.fetchone()
        #Si hay foto eliminamos la foto 
        if foto_url and foto_url['foto']:
            #Borramos la foto que este guardada del perfil
            os.remove(os.path.join(UPLOAD_FOLDER, foto_url['foto']))

        student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(id))

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

        db_path = f"estudiantes/{id}/{foto_perfil}"

        query = "UPDATE estudiantes SET foto = %s WHERE id = %s"
        cursor.execute(query, (db_path, id))
        conn.commit()

        return {'message': 'Foto actualizada correctamente'}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route('/student/<int:id>', methods=['PUT'])
def update_student(id):
    conn = None
    cursor = None
    if not request.is_json:
        return {'error': 'Falta el JSON en la solicitud'}, 400
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

        if data.get('accesibilidad'):
            accesibilidad = data.get('accesibilidad')
            if isinstance(accesibilidad, list):
                accesibilidad_str = ','.join([a.strip() for a in accesibilidad if a])
            else:
                accesibilidad_str = str(accesibilidad).strip()
            
            if accesibilidad_str:
                fields.append("accesibilidad = %s")
                params.append(accesibilidad_str)
        
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

        return {'message': 'Estudiante actualizado correctamente'}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route("/student/<int:id>/image-password", methods=['DELETE'])
def clear_image_password(id):
    conn = None
    cursor = None
    try:
        # 1. Eliminar archivos del directorio
        student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(id), 'contraseñaImagen')
        if os.path.exists(student_dir):
            shutil.rmtree(student_dir)

        # 2. Eliminar registros de la base de datos
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contraseña_imagenes_estudiante WHERE id_estudiante = %s", (id,))
        conn.commit()

        return {'ok': True, 'message': 'Contraseña por imagen eliminada correctamente'}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@students.route("/student/<int:id>/image-password", methods=['POST'])
def imagen_password(id):
    conn = None
    cursor = None
    try: 
        
        if 'photo' not in request.files: 
            return {'error': 'No photo uploaded'}, 400
        photo = request.files['photo']
        if photo.filename == '': 
            return {'error': 'No photo selected'}, 400
        base_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(id))

        student_dir = os.path.join(base_dir, 'contraseñaImagen')
        
        if not os.path.exists(student_dir): 
            os.makedirs(student_dir) # Si no existe crea el directorio 
        
        
        codigo = request.form.get('codigo')
        es_contraseña = request.form.get('es_contraseña') == 'true'
        
        
        filename = secure_filename(photo.filename)
        
        file_path = os.path.join(student_dir, filename)

        photo.save(file_path)

        query = """INSERT INTO contraseña_imagenes_estudiante (id_estudiante, url_imagen, codigo, es_contraseña)
                    VALUES (%s, %s, %s, %s)"""
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, (id, file_path, codigo, es_contraseña))
        conn.commit()

        return {'ok': True, 'message': 'Foto subida exitosamente'}, 200
    except Exception as e: 
        return {'error': str(e)}, 500
    
@students.route("/student/<int:id>/contraseña-imagen")
def get_image_password(id):
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        # Usamos el cursor normal, sin parámetros extra que den error
        cursor = conn.cursor()
        
        query = """
            SELECT url_imagen, id 
            FROM contraseña_imagenes_estudiante 
            WHERE id_estudiante = %s
        """
        cursor.execute(query, (id,))

        filas = cursor.fetchall()
        print(filas)

        imagenes = []
        for fila in filas:
            imagenes.append({
                'uri': fila['url_imagen'],
                'id': fila['id'],
            })
        
        random.shuffle(imagenes)
        return {'ok': True, 'message': imagenes}, 200

    except Exception as e: 
        return {'ok': False, 'error': str(e)}, 500
    finally: 
        if conn: 
            cursor.close()
            conn.close()

@students.route("/student/<int:id>/trofeos")
def get_trofeos(id):
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        
        query = "SELECT puntos FROM estudiantes WHERE id = %s"
        cursor.execute(query, (id,))
        fila = cursor.fetchone()

        if not fila:
            return {'ok': False, 'error': 'Estudiante no encontrado'}, 404
        
        puntos = fila['puntos']
        return {'ok': True, 'puntos': puntos}, 200

    except Exception as e: 
        return {'ok': False, 'error': str(e)}, 500
    finally: 
        if conn: 
            cursor.close()
            conn.close()