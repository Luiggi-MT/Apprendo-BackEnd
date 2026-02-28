from flask import Blueprint, request, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from flask_jwt_extended import get_jwt_identity
from werkzeug.security import check_password_hash

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

        query = "SELECT password, foto, tipo, id FROM profesores WHERE username = %s"
        cursor.execute(query, (username,))
        profesor = cursor.fetchone()

        if profesor == None: 
            return {'error': 'Usuario no encontrado'}, 401

        if profesor and check_password_hash(profesor['password'], password):
            
            claims = {
                "foto": profesor['foto'],
                "tipo": profesor['tipo'],
                "id": profesor['id'],
            }
            
            access_token = create_access_token(identity=username, additional_claims=claims, fresh=True)
            expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
            return {
                'access_token': access_token,
                'username': username, 
                'foto': profesor['foto'], 
                'tipo': profesor['tipo'], 
                'id': profesor['id'],
                "expires_in": int(expires.total_seconds()),
            }, 200
        
        return {'error': 'Contraseeña incorrecta'}, 401

    except Exception as e:
        return {'error': str(e)}, 500
    finally: 
        if conn:
            cursor.close()
            conn.close()

@auth.route('/login_student', methods=['POST'])
def login_student(): 
    if not request.is_json: 
        return {'error': 'Missing JSON in request'}, 400
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        data = request.get_json()
        student_id = data.get('id')
        query = """SELECT * FROM estudiantes WHERE id = %s"""
        cursor.execute(query, (student_id, ))
        student = cursor.fetchone()
        is_authenticated = False
        
        if not student:
            return {'error': 'Estudiante no encontrado'}, 404

        tipoContraseña = data.get('tipoContraseña')
        if(tipoContraseña == "imagenes"):
            if(data.get('passwordImage')): 
                passwordImage = data.get('passwordImage') 
                query = f"""SELECT id FROM contraseña_imagenes_estudiante WHERE id_estudiante = %s AND es_contraseña = 1"""
                cursor.execute(query, (student_id))
                imagenes = cursor.fetchall() 
                    
                user_ids = {img['id'] for img in passwordImage}

                db_ids = {img['id'] for img in imagenes}

                if user_ids == db_ids: 
                    is_authenticated = True
                else: 
                    fallos = list(user_ids - db_ids)
                    return {'error' : 'Contraseña incorrecta', 'fallos' : fallos}, 401
        else:
            if(data.get('password')):
                password = data.get('password')
                if check_password_hash(student['contraseña'], password):
                    is_authenticated = True
        if is_authenticated: 
            claims = {
                "foto": student['foto'],
                "tipo": "estudiante",
                "tipoContraseña": student['tipoContraseña'],
                "accesibilidad": student['accesibilidad'],
                "preferenciasVisualizacion": student['preferenciasVisualizacion'],
                "asistenteVoz": student['asistenteVoz'],
                "id": student['id']
            }
            access_token = create_access_token(identity=student['username'], additional_claims=claims, fresh=True)
            expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
            return {
                "access_token": access_token,
                "id": student["id"],
                "username": student["username"],
                "foto": student["foto"],
                "tipo": "estudiante", 
                "expires_in": int(expires.total_seconds()),

            }, 200
        return {'error': 'Contraseña incorrecta'}, 401
    except Exception as e:
        return {'error': str(e)}, 500
    finally: 
        if conn:
            cursor.close()
            conn.close()

@auth.route('/logout', methods=['POST'])
def logout():
    # Con JWT, el logout se hace en el cliente borrando el token.
    # Si quieres invalidarlo en el servidor, necesitarías una Blacklist (Redis).
    return {'message': 'Logout exitoso'}, 200

@auth.route('/session')
@jwt_required()
def get_session(): 
   
    current_user = get_jwt_identity()
    claims = get_jwt()
    
    return {
        'ok' : True,
        'username': current_user, 
        'foto': claims.get('foto'), 
        'tipo': claims.get('tipo'),
        "tipoContraseña": claims.get('tipoContraseña'),
        "accesibilidad": claims.get('accesibilidad'),
        "preferenciasVisualizacion": claims.get('preferenciasVisualizacion'),
        "asistenteVoz": claims.get('asistenteVoz'),
        "id": claims.get('id')
    }, 200