from flask import Blueprint, request
from db import Database
from const import LIMIT
from flask_jwt_extended import jwt_required, get_jwt

db = Database()
aulas = Blueprint('aulas', __name__)


@aulas.route('/aulas')
@jwt_required()
def get_aulas():
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'profesor' and claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
            return {"error": "Acceso no autorizado"}, 403
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
            return {"error": "offset o limit invalidos"}, 400

        query = "SELECT id, nombre FROM aulas ORDER BY (UPPER(nombre) = 'ALMACEN') DESC, nombre LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM aulas")
        total = cursor.fetchone()
        total_count = total[0] if isinstance(
            total, tuple) else list(total.values())[0]
        aulas = []
        for row in rows:
            aulas.append({
                "id": row['id'],
                "nombre": row['nombre']
            })

        return {
            'aulas': aulas,
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


@aulas.route('/aulas', methods=['POST'])
@jwt_required()
def create_aula():
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        data = request.get_json()
        nombre = data.get('nombre')
        if not nombre:
            return {"error": "El nombre es necesario"}, 400
        conn = db.connect()
        cursor = conn.cursor()
        query = "INSERT INTO aulas (nombre) VALUES (%s)"
        cursor.execute(query, (nombre,))
        conn.commit()
        return {"message": "Aula creada correctamente"}, 201
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/aulas/buscar')
@jwt_required()
def get_aula_by_name():
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        nombre = request.args.get('nombre', '')
        if not nombre:
            return {"error": "El nombre es necesario"}, 400
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
            return {"error": "offset o limit invalidos"}, 400

        query = "SELECT id, nombre FROM aulas WHERE nombre LIKE %s LIMIT %s OFFSET %s"
        cursor.execute(query, ('%' + nombre + '%', limit, offset))
        rows = cursor.fetchall()
        cursor.execute(
            "SELECT COUNT(*) FROM aulas WHERE nombre LIKE %s", ('%' + nombre + '%',))
        total = cursor.fetchone()
        total_count = total[0] if isinstance(
            total, tuple) else list(total.values())[0]
        aulas = []
        for row in rows:
            aulas.append({
                "id": row['id'],
                "nombre": row['nombre']
            })

        return {
            'aulas': aulas,
            'total': total_count,
            'offset': offset,
        }, 200

    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/aulas/<int:id>')
@jwt_required()
def get_aula_by_id(id):
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'profesor' and claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
            return {"error": "Acceso no autorizado"}, 403
        conn = db.connect()
        cursor = conn.cursor()
        query = f"""SELECT a.id, a.nombre, pa.id_profesor
                FROM aulas a
                LEFT JOIN profesor_aula pa ON a.id = pa.id_aula
                WHERE a.id = %s"""
        cursor.execute(query, (id, ))
        aula = cursor.fetchone()
        if not aula:
            return {"error": "Aula no encontrada"}, 404
        return aula, 200
    except Exception as e:
        return {"errro": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/aulas/asignar-profesor', methods=['POST'])
@jwt_required()
def asignar_profesor_aula():
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        print(claims)
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        data = request.get_json()
        aula_id = data.get('aula_id')
        profesor_id = data.get('profesor_id')
        if not aula_id or not profesor_id:
            return {"error": "aula_id and profesor_id are required"}, 400

        conn = db.connect()
        cursor = conn.cursor()
        query = "INSERT INTO profesor_aula (id_aula, id_profesor) VALUES (%s, %s)"
        cursor.execute(query, (aula_id, profesor_id))
        conn.commit()
        return {"message": "Profesor assigned to Aula successfully"}, 200
    except Exception as e:
        print(f"Error asignando profesor a aula: {e}")
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/aulas/eliminar-profesor', methods=['POST'])
@jwt_required()
def eliminar_profesor_aula():
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        data = request.get_json()
        aula_id = data.get('aula_id')
        profesor_id = data.get('profesor_id')
        if not aula_id:
            return {"error": "aula_id es necesario"}, 400

        if not profesor_id:
            return {"error": "profesor_id es necesario"}, 400

        conn = db.connect()
        cursor = conn.cursor()

        query = "DELETE FROM profesor_aula WHERE id_aula = %s AND id_profesor = %s"
        cursor.execute(query, (aula_id, profesor_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return {"message": "No había ningún profesor vinculado a esta aula"}, 200

        return {"message": "Profesor desvinculado con éxito"}, 200

    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/delete-aula/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_aula(id):
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin':
            return {"error": "Acceso no autorizado"}, 403
        conn = db.connect()
        cursor = conn.cursor()

        # 1. Primero eliminamos las vinculaciones en la tabla intermedia (si existen)
        # Esto evita errores de llave foránea si no usaste ON DELETE CASCADE
        query_relacion = "DELETE FROM profesor_aula WHERE id_aula = %s"
        cursor.execute(query_relacion, (id,))

        # 2. Eliminamos el aula de la tabla aulas
        query_aula = "DELETE FROM aulas WHERE id = %s"
        cursor.execute(query_aula, (id,))

        conn.commit()

        if cursor.rowcount == 0:
            return {"error": "El aula no existe"}, 404

        return {"message": "Aula eliminada correctamente"}, 200

    except Exception as e:
        if conn:
            conn.rollback()  # Deshacer cambios si algo sale mal
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/almacen', methods=['POST'])
@jwt_required()
def create_almacen():
    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "INSERT INTO aulas (nombre) VALUES ('ALMACEN')"
        cursor.execute(query)
        conn.commit()
        return {"message": "Almacen creado correctamente"}, 201
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/almacen', methods=['DELETE'])
@jwt_required()
def delete_almacen():
    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "DELETE FROM aulas WHERE nombre = 'ALMACEN'"
        cursor.execute(query)
        conn.commit()
        return {"message": "Almacen eliminado correctamente"}, 200
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/almacen')
@jwt_required()
def get_almacen():
    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "SELECT id FROM aulas WHERE nombre = 'ALMACEN'"
        cursor.execute(query)
        almacen = cursor.fetchone()
        if almacen:
            return {"almacen": True}, 200
        else:
            return {"almacen": False}, 200
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@aulas.route('/aula/tarea-material', methods=['POST'])
@jwt_required()
def get_aulas_tarea_material():
    claims = get_jwt()
    if claims.get('tipo') != 'profesor' and claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {"error": "Acceso no autorizado"}, 403

    data = request.get_json()
    tarea_id = data.get('id_tarea')
    fecha = data.get('fecha')
    estudiante_id = data.get('id_estudiante')
    if not all([tarea_id, fecha, estudiante_id]):
        return {"error": "id_tarea, fecha e id_estudiante son necesarios"}, 400

    query = """SELECT aula_id FROM visita_aula 
                WHERE tarea_id = %s AND estudiante_id = %s AND fecha = %s"""
    try:
        visitadas = db.fetch_query(query, (tarea_id, estudiante_id, fecha))
        print(f"Aulas visitadas: {visitadas}")
    except Exception as e:
        print(f"Error al obtener aulas visitadas para tarea y material: {e}")
        return {"error": str(e)}, 500

    if len(visitadas) != 2:

        query = f"""SELECT profesor_id FROM pedido 
                    WHERE estudiante_id = %s AND fecha = %s"""
        try:
            pedido = db.fetch_query(
                query, (estudiante_id, fecha), fetchone=True)
            print(f"Pedido encontrado: {pedido}")
        except Exception as e:
            print(f"Error al obtener pedido para estudiante y fecha: {e}")
            return {"error": str(e)}, 500

        query = """SELECT id_aula as id FROM profesor_aula 
                    WHERE id_profesor = %s"""
        try:
            aulas_profesor = db.fetch_query(
                query, (pedido['profesor_id'],), fetchone=True)
            print(f"Aulas del profesor: {aulas_profesor}")
        except Exception as e:
            print(f"Error al obtener aulas del profesor: {e}")
            return {"error": str(e)}, 500
        if not aulas_profesor:
            return {"aulas": []}, 200
        query = """SELECT aula_id FROM visita_aula WHERE tarea_id = %s AND estudiante_id = %s AND fecha = %s AND aula_id = %s"""
        try:
            exist = db.fetch_query(
                query, (tarea_id, estudiante_id, fecha, aulas_profesor['id']), fetchone=True)
            print(f"Visita a aula del profesor ya registrada")
        except Exception as e:
            print(f"Error al verificar visita a aula del profesor: {e}")
            return {"error": str(e)}, 500
        if not exist:
            query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id) VALUES (%s, %s, %s, %s)"""
            try:
                db.execute_query(query, (tarea_id, estudiante_id,
                                         fecha, aulas_profesor['id']))
                print(
                    f"Registro de visita_aula creado para tarea {tarea_id}, estudiante {estudiante_id}, fecha {fecha}, aula {aulas_profesor['id']}")
            except Exception as e:
                print(f"Error al crear registro de visita_aula: {e}")
                return {"error": str(e)}, 500
        query = """SELECT * FROM aulas WHERE nombre = 'ALMACEN'"""
        try:
            almacen = db.fetch_query(query, fetchone=True)
            print(f"Almacen encontrado: {almacen}")
        except Exception as e:
            print(f"Error al obtener almacen: {e}")
            return {"error": str(e)}, 500
        if almacen:
            query = """SELECT aula_id FROM visita_aula WHERE tarea_id = %s AND estudiante_id = %s AND fecha = %s AND aula_id = %s"""
            try:
                exist = db.fetch_query(
                    query, (tarea_id, estudiante_id, fecha, almacen['id']), fetchone=True)
                print(f"Visita a almacen ya registrada")
            except Exception as e:
                print(f"Error al verificar visita a almacen: {e}")
                return {"error": str(e)}, 500
            if not exist:
                query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id) VALUES (%s, %s, %s, %s)"""
                try:
                    db.execute_query(
                        query, (tarea_id, estudiante_id, fecha, almacen['id']))
                    print(
                        f"Registro de visita_aula creado para tarea {tarea_id}, estudiante {estudiante_id}, fecha {fecha}, aula {almacen['id']}")
                except Exception as e:
                    print(
                        f"Error al crear registro de visita_aula para almacen: {e}")
                    return {"error": str(e)}, 500

    query = """SELECT va.aula_id, va.visitado, a.nombre AS aula, p.username, p.foto
                FROM visita_aula va
                JOIN aulas a ON va.aula_id = a.id
                LEFT JOIN profesor_aula pa ON a.id = pa.id_aula
                LEFT JOIN profesores p ON pa.id_profesor = p.id
                WHERE va.tarea_id = %s AND va.estudiante_id = %s AND va.fecha = %s
                ORDER BY (UPPER(a.nombre) = 'ALMACEN') DESC, a.nombre ASC"""
    try:
        aulas = db.fetch_query(query, (tarea_id, estudiante_id, fecha))
        print(f"Aulas {aulas}")
    except Exception as e:
        print(f"Error al obtener aulas para tarea y material: {e}")
        return {"error": str(e)}, 500

    return {"aulas": aulas}, 200


@aulas.route('/aula/visitar', methods=['POST'])
@jwt_required()
def visitar_aula():
    claims = get_jwt()
    if claims.get('tipo') != 'profesor' and claims.get('tipo') != 'admin' and claims.get('tipo') != 'estudiante':
        return {"error": "Acceso no autorizado"}, 403
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        data = request.get_json()
        aula_id = data.get('aula_id')
        estudiabte_id = data.get('estudiante_id')
        fecha = data.get('fecha')
        print(data)
        if aula_id is None or estudiabte_id is None or fecha is None:
            return {"error": "aula_id, estudiante_id y fecha son necesarios"}, 400

        query = """UPDATE visita_aula SET visitado = TRUE
                WHERE estudiante_id = %s AND fecha = %s AND aula_id = %s"""
        cursor.execute(query, (estudiabte_id, fecha, aula_id))
        conn.commit()
        return {"message": "Aula marcada como visitada correctamente"}, 200
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
