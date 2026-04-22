from flask import Blueprint, request
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.utils import secure_filename
from db import Database
from const import LIMIT

db=Database()
profesor = Blueprint('profesor', __name__)

@profesor.route('/profesores')
def get_profesores():
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        cursor = conn.cursor()
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
        except ValueError:
            return {"error": "Invalid offset or limit"}, 400
        
        query = "SELECT id, username, foto FROM profesores LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM profesores")
        total = cursor.fetchone()
        total_count = total[0] if isinstance(total, tuple)  else list(total.values())[0]
        profesores = []
        for row in rows:
            profesores.append({
                "id": row['id'],
                "username": row['username'],
                "foto" : row['foto'],
                })

        return {
            'profesores': profesores,
            'total': total_count,
            'offset': offset + limit,
        }, 200
       
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@profesor.route('/profesores/<int:id>', methods=['GET'])
@jwt_required()
def get_profesor_by_id(id): 
    conn = None
    cursor = None 
    try: 
        claims = get_jwt()
        if claims.get('tipo') != 'profesor' and claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        conn = db.connect()
        cursor = conn.cursor()
        query = f"""SELECT username, foto, id FROM profesores WHERE id = %s"""
        cursor.execute(query, (id,))
        profesor = cursor.fetchone()
        return profesor, 200
    except Exception as e: 
        return {"error" : str(e)}, 500
    finally: 
        if cursor: 
            cursor.close() 
        if conn: 
            conn.close()

@profesor.route('/profesores/create', methods=['POST'])
@jwt_required()
def create_profesor(): 
    conn = None
    cursor = None
    if not request.is_json: 
        return {"error": "Missing JSON in request"}, 400
    
    try: 
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        data = request.get_json()
        username = data.get('username')
        palabra_clave = data.get('palabra-clave', 'PROFESOR') # Valor por defecto si no viene
        tipo = data.get('tipo', 'profesor')
        foto = data.get('foto', 'porDefecto.png')
        
        if not username:
            return {"error": "El nombre de usuario es obligatorio"}, 400

       

        conn = db.connect()
        cursor = conn.cursor()

        query = """
            INSERT INTO profesores (username, palabra_clave, tipo, foto) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (username, palabra_clave, tipo, foto))
        conn.commit()

        return {"message": "Profesor creado exitosamente", "id": cursor.lastrowid}, 201

    except Exception as e: 
        if conn:
            conn.rollback()
        return {'error': str(e)}, 500
    finally: 
        if cursor: 
            cursor.close() 
        if conn: 
            conn.close()

@profesor.route('/profesores/contraseña', methods=['POST'])
def update_password():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        username = data.get('username')
        new_password = data.get('password')
        palabra_clave = data.get('palabra-clave') # Coincide con tu JSON de React

        if not username or not new_password or not palabra_clave:
            return {"error": "Todos los campos son obligatorios"}, 400

        conn = db.connect()
        cursor = conn.cursor()

        # 1. Buscamos al profesor por username para verificar su palabra clave
        query_check = "SELECT palabra_clave FROM profesores WHERE username = %s"
        cursor.execute(query_check, (username,))
        user = cursor.fetchone()
      
        if not user:
            return {"error": "Usuario no encontrado"}, 404

        # 2. Verificamos si la palabra clave coincide (puedes usar check_password_hash si la hasheaste)
        if user['palabra_clave'] != palabra_clave:
            return {"error": "La palabra clave es incorrecta"}, 401

        # 3. Si todo es correcto, hasheamos la nueva contraseña y actualizamos
        hashed_pw = generate_password_hash(new_password, method='pbkdf2:sha256')
        query_update = "UPDATE profesores SET password = %s WHERE username = %s"
        cursor.execute(query_update, (hashed_pw, username))
        
        conn.commit()

        return {"message": "Contraseña actualizada correctamente"}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@profesor.route('/profesores/buscar')
def get_profesor_by_name(): 
    conn = None
    cursor = None 
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        name = request.args.get('name', '')
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', LIMIT))
        query = f"""SELECT username, foto, id FROM profesores WHERE username LIKE %s ORDER BY username LIMIT %s OFFSET %s"""
        cursor.execute(query, (f"%{name}%", limit, offset))
        profesores = cursor.fetchall()
        query = f"""SELECT COUNT(*) FROM profesores WHERE username LIKE %s"""
        cursor.execute(query, (f"%{name}%",))
        total = cursor.fetchone()['COUNT(*)']
        return {"profesores": profesores, "offset": offset, "limit": limit, "total": total}, 200
    except Exception as e: 
        return {"error" : str(e)}, 500
    finally: 
        if cursor: 
            cursor.close() 
        if conn: 
            conn.close()

@profesor.route('/profesores/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_profesor(id):
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        conn = db.connect()
        cursor = conn.cursor()
        query = """SELECT tipo FROM profesores WHERE id = %s"""
        cursor.execute(query, (id,))
        profesor = cursor.fetchone()
        if not profesor:
            return {"error": "Profesor no encontrado"}, 404
        if profesor['tipo'] == 'admin':
            return {"error": "No se puede eliminar a un profesor con rol admin"}, 403
        query = "DELETE FROM profesores WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": "Profesor no encontrado"}, 404
        return {"message": "Profesor eliminado exitosamente"}, 200
    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()