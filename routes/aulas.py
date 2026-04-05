from flask import Blueprint, request
from db import Database
from const import LIMIT

db=Database()
aulas = Blueprint('aulas', __name__)

@aulas.route('/aulas')
def get_aulas():
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
            return {"error": "offset o limit invalidos"}, 400
        
        query = "SELECT id, nombre FROM aulas LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM aulas")
        total = cursor.fetchone()
        total_count = total[0] if isinstance(total, tuple)  else list(total.values())[0]
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
def create_aula():
    conn = None
    cursor = None
    try:
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
def get_aula_by_name():
    conn = None
    cursor = None
    try: 
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
        cursor.execute("SELECT COUNT(*) FROM aulas WHERE nombre LIKE %s", ('%' + nombre + '%',))
        total = cursor.fetchone()
        total_count = total[0] if isinstance(total, tuple)  else list(total.values())[0]
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
def get_aula_by_id(id): 
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        query = f"""SELECT a.id, a.nombre, pa.id_profesor
                FROM aulas a
                LEFT JOIN profesor_aula pa ON a.id = pa.id_aula
                WHERE a.id = %s"""
        cursor.execute(query, (id, ))
        aula = cursor.fetchone()
        if not aula: 
            return {"error" : "Aula no encontrada"}, 404
        return aula, 200
    except Exception as e: 
        return {"errro" : str(e)}, 500
    finally: 
        if cursor: 
            cursor.close()
        if conn: 
            conn.close()
            
@aulas.route('/aulas/asignar-profesor', methods=['POST'])
def asignar_profesor_aula():
    conn = None
    cursor = None
    try:
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
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@aulas.route('/aulas/eliminar-profesor', methods=['POST'])
def eliminar_profesor_aula():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        aula_id = data.get('aula_id')
        profesor_id = data.get('profesor_id')
        if not aula_id:
            return {"error": "aula_id es necesario"}, 400
        
        if not profesor_id: 
            return {"error" : "profesor_id es necesario"}, 400
        
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
def delete_aula(id):
    conn = None
    cursor = None
    try:
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
            conn.rollback() # Deshacer cambios si algo sale mal
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@aulas.route('/almacen', methods=['POST'])
def create_almacen():
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
def delete_almacen():
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
def get_almacen():
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
def get_aulas_tarea_material(): 
    conn = None
    cursor = None
    try: 
        data = request.get_json()
        tarea_id = data.get('id_tarea')
        fecha = data.get('fecha')
        estudiante_id = data.get('id_estudiante')
        if not tarea_id: 
            return {"error": "tarea_id es necesario"}, 400
        if not fecha: 
            return {"error": "fecha es necesaria"}, 400
        if not estudiante_id:
            return {"error": "estudiante_id es necesario"}, 400
        conn = db.connect()
        cursor = conn.cursor()

        query = """SELECT va.aula_id, va.visitado, a.nombre AS aula, p.username, p.foto
                FROM visita_aula va
                JOIN aulas a ON va.aula_id = a.id
                LEFT JOIN profesor_aula pa ON a.id = pa.id_aula
                LEFT JOIN profesores p ON pa.id_profesor = p.id
                WHERE va.tarea_id = %s AND va.estudiante_id = %s AND va.fecha = %s
                ORDER BY (UPPER(a.nombre) = 'ALMACEN') DESC, a.nombre ASC"""
        cursor.execute(query, (tarea_id, estudiante_id, fecha))
        aulas = cursor.fetchall()

        return {"aulas": aulas}, 200
    except Exception as e:
        print(f"Error al obtener aulas para tarea y material: {e}")
        return {"error": str(e)}, 500
    finally: 
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@aulas.route('/aula/visitar', methods=['POST'])
def visitar_aula():
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