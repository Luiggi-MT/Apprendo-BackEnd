from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from db import Database
from const import LIMIT, OFFSET

import random
import os
import glob
import shutil

db = Database()
UPLOAD_FOLDER = os.getenv('FILE_PATH')

students = Blueprint('students', __name__)



@students.route('/students')
def get_students():
    offset = int(request.args.get('offset', OFFSET))
    limit = int(request.args.get('limit', LIMIT))
    try: 
        students = db.fetch_query(
            f"""SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz, id 
                FROM estudiantes 
                LIMIT %s OFFSET %s""",
            (limit, offset)
        )
     
        count_result = db.fetch_query("SELECT COUNT(*) FROM estudiantes", fetchone=True)
    
        total_count = count_result['COUNT(*)'] if count_result else 0

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

@students.route('/student/<string:username>', methods=['DELETE'])
@jwt_required()
def delete_student(username): 
    claims = get_jwt()

    if claims.get('tipo') != 'admin':
        return {"Error": "Acceso denegado. Solo los administradores pueden eliminar estudiantes."}, 403
    
    
    try: 
        student = db.fetch_query(f"SELECT id FROM estudiantes WHERE username = %s", (username, ), fetchone=True)
    except Exception as e:
        return {"Error": str(e)}, 500
    
    if not student: 
        return {"Error": "Student not found"}, 404
    
    try:
        db.execute_query(f"DELETE FROM estudiantes WHERE id = %s", (student['id'], ))
    except Exception as e:
        return {"Error": str(e)}, 500
    try: 
        deleted = db.fetch_query(f"SELECT id FROM estudiantes WHERE id = %s", (student['id'], ), fetchone=True)
    except Exception as e:
        return {"Error": str(e)}, 500
    
    if deleted: 
        return {"Error": "No se ha podido eliminar al estudiante"}, 400
    
    student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(student['id']))
            
    if os.path.exists(student_dir): 
        try: 
            shutil.rmtree(student_dir)
        except Exception as dir_error:
            print(f"Error borrando directorio: {dir_error}")
        
    return {"message": "Estudiante eliminado correctamente"}, 200



@students.route('/students/<string:username>')
def get_student(username): 
    offset = int(request.args.get('offset', OFFSET))
    limit = int(request.args.get('limit', LIMIT))
    try: 
        students = db.fetch_query(
            f"""SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz 
                FROM estudiantes 
                WHERE username LIKE %s
                ORDER BY username
                LIMIT %s OFFSET %s""",
            (f"%{username}%", limit, offset)
        )
     
        count_result = db.fetch_query("SELECT COUNT(*) FROM estudiantes WHERE username LIKE %s", (f"%{username}%",), fetchone=True)

        total_count = count_result['COUNT(*)'] if count_result else 0
            
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
        return {'students': students_list, 'offset': offset + limit, 'count': total_count}, 200

    except Exception as e:
        return {'error': str(e)}, 500    

@students.route('/student', methods=['POST'])
@jwt_required()
def create_student():
    claims = get_jwt()

    if claims.get('tipo') != 'admin':
        return {'error': 'Acceso denegado. Solo los administradores pueden crear estudiantes.'}, 403
    
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    
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
        accesibilidad_str = ','.join([a.strip() for a in accesibilidad]) if isinstance(accesibilidad, list) else accesibilidad.strip()
        fields.append('accesibilidad')
        params.append(accesibilidad_str)


    placeholders = ",".join(["%s"] * len(fields))
    nombre_columnas = ", ".join(fields)

    query = f"INSERT INTO estudiantes ({nombre_columnas}) VALUES ({placeholders})"
    try: 
        db.execute_query(query, params)
        id_estudiante = db.fetch_query("SELECT LAST_INSERT_ID() AS id", fetchone=True)['id']

        return {
            'message': 'Estudiante creado correctamente', 
            'id': id_estudiante,
            'ok': True
        }, 201
    except Exception as e:
        return {'error': str(e)}, 500


@students.route('/student/<int:id>/photo', methods=['POST'])
@jwt_required()
def upload_student_photo(id):
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {'error': 'Acceso denegado. Solo los administradores y los estudiantes pueden subir fotos de estudiantes.'}, 403

    if 'photo' not in request.files:
        return {'error': 'No photo uploaded'}, 400

    photo = request.files['photo']
    if photo.filename == '':
        return {'error': 'No photo selected'}, 400
    
    try: 
        foto_url = db.fetch_query("SELECT foto FROM estudiantes WHERE id = %s", (id,), fetchone=True)
    except Exception as e:
        return {'error': str(e)}, 500
    
    #Si hay foto eliminamos la foto 
    if foto_url and foto_url['foto'] and foto_url['foto'] != 'porDefecto.png':
        old_path = os.path.join(UPLOAD_FOLDER, foto_url['foto'])
        if os.path.exists(old_path):
            os.remove(old_path)

    student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(id))
    contrasena_dir = os.path.join(student_dir, 'contraseñaImagen')

    if not os.path.exists(student_dir):
        os.makedirs(student_dir)  # Crear el directorio si no existe
    if not os.path.exists(contrasena_dir):
        os.makedirs(contrasena_dir)  # Crear subdirectorio de contraseña
        
        
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
    try: 
        db.execute_query(query, (db_path, id))
    except Exception as e:
        return {'error': str(e)}, 500

    return {'message': 'Foto actualizada correctamente'}, 200

@students.route('/student/<int:id>', methods=['PUT'])
@jwt_required()
def update_student(id):
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {'error': 'Acceso denegado. Solo los administradores y los estudiantes pueden actualizar los datos del estudiante.'}, 403

    if not request.is_json:
        return {'error': 'Falta el JSON en la solicitud'}, 400
        
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

    try: 
        db.execute_query(query, params)
    except Exception as e:
        return {'error': str(e)}, 500

    return {'message': 'Estudiante actualizado correctamente'}, 200

@students.route("/student/<int:id>/image-password", methods=['DELETE'])
@jwt_required()
def clear_image_password(id):
        
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {'error': 'Acceso denegado. Solo los administradores y los estudiantes pueden eliminar la contraseña por imagen.'}, 403
        
    # 1. Eliminar archivos del directorio
    student_dir = os.path.join(UPLOAD_FOLDER, 'estudiantes', str(id), 'contraseñaImagen')
    if os.path.exists(student_dir):
        shutil.rmtree(student_dir)

    # 2. Eliminar registros de la base de datos
    try: 
        query = "DELETE FROM contraseña_imagenes_estudiante WHERE id_estudiante = %s"
        db.execute_query(query, (id,))
        deleted = db.fetch_query("SELECT id FROM contraseña_imagenes_estudiante WHERE id_estudiante = %s", (id,), fetchone=True)
        if deleted: 
            return {'error': 'No se ha podido eliminar la contraseña por imagen'}, 400
    except Exception as e:
        return {'error': str(e)}, 500

    return {'ok': True, 'message': 'Contraseña por imagen eliminada correctamente'}, 200

@students.route("/student/<int:id>/image-password", methods=['POST'])
@jwt_required()
def imagen_password(id):
        
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {'error': 'Acceso denegado. Solo los administradores y los estudiantes pueden subir la contraseña por imagen.'}, 403
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
    db_path = f"estudiantes/{id}/contraseñaImagen/{filename}"

    photo.save(file_path)

    query = """INSERT INTO contraseña_imagenes_estudiante (id_estudiante, url_imagen, codigo, es_contraseña)
                VALUES (%s, %s, %s, %s)"""
        
    try: 
        db.execute_query(query, (id, db_path, codigo, es_contraseña))
    except Exception as e:
        return {'error': str(e)}, 500
        
    # Verificar que se ha insertado correctamente
    inserted = db.fetch_query("SELECT id FROM contraseña_imagenes_estudiante WHERE id_estudiante = %s AND url_imagen = %s", (id, db_path), fetchone=True)
    if not inserted: 
        return {'error': 'No se ha podido subir la contraseña por imagen'}, 400

    return {'ok': True, 'message': 'Foto subida exitosamente'}, 200
    
    
@students.route("/student/<int:id>/contraseña-imagen")

def get_image_password(id): 
        
    query = """
            SELECT url_imagen, id 
            FROM contraseña_imagenes_estudiante 
            WHERE id_estudiante = %s
            """
    try:    
        filas = db.fetch_query(query, (id,))

    except Exception as e:
        return {'error': str(e)}, 500

    imagenes = []

    for fila in filas:
        imagenes.append({
            'uri': fila['url_imagen'],
            'id': fila['id'],
        })
        
    random.shuffle(imagenes)
    return {'ok': True, 'message': imagenes}, 200

@students.route("/student/<int:id>/trofeos")
@jwt_required()
def get_trofeos(id):
    
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {'error': 'Acceso denegado. Solo los administradores y los estudiantes pueden obtener los trofeos.'}, 403
        
        
    query = "SELECT puntos FROM estudiantes WHERE id = %s"
    fila = db.fetch_query(query, (id,), fetchone=True)

    if not fila:
        return {'ok': False, 'error': 'Estudiante no encontrado'}, 404
        
    puntos = fila['puntos']
    return {'ok': True, 'puntos': puntos}, 200