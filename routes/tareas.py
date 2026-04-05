from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
from db import Database
from const import LIMIT
from routes.notificaciones import enviar_push
from routes.materialEscolar import _color_name_from_hex

db = Database()

tareas = Blueprint('tareas', __name__)

@tareas.route('/tareas')
def get_tareas(): 
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
        if limit<=0: 
            limit = LIMIT
    except (ValueError, TypeError): 
        limit = LIMIT

    try: 
        conn = db.connect()
        cursor = conn.cursor()
        tareas_total = []

        query = f"""SELECT id, id_pictograma, nombre, categoria  FROM tarea LIMIT %s OFFSET %s"""

        cursor.execute(query, (limit, offset))
        tareas = cursor.fetchall()

        tareas_list = []

        for tarea in tareas: 
            tareas_list.append({
                'id' : tarea['id'],
                'id_pictograma': tarea['id_pictograma'],
                'nombre': tarea['nombre'], 
                'categoria': tarea['categoria'],
            })
        count = len(tareas_total)
        return{
            'tareas': tareas_list, 
            'offset': offset + limit, 
            'count': count,
        }, 200

    except Exception as e:
        print(str(e))
        return {'error': str(e)}, 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@tareas.route('/tareas-comanda', methods=['GET'])
def get_comanda_info():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        # Buscamos la tarea tipo comanda y traemos la nota de la asignación
        query = """
            SELECT count(*) FROM tarea WHERE categoria = 'comanda' """
        cursor.execute(query)
        result = cursor.fetchone()
        count = result['count(*)']
        if count == 0:
            return { 'exists' : False }, 200

        return {'exists' : True }, 200

    except Exception as e:
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
@tareas.route('/tareas-material-escolar', methods=['POST'])
def create_material_escolar_base():
    conn = None
    cursor = None
    try:

        conn = db.connect()
        cursor = conn.cursor()
        id_pictograma = 34153
        nombre = 'pedido material'
        categoria = 'material_escolar'

        query = "INSERT INTO tarea (id_pictograma, nombre, categoria) VALUES (%s, %s, %s)"
        cursor.execute(query, (id_pictograma, nombre, categoria, ))     
        conn.commit()
        id_tarea = cursor.lastrowid
        query = "INSERT INTO pedido_material (id, id_pictograma, nombre) VALUES (%s, %s, %s)"
        cursor.execute(query, (id_tarea, id_pictograma, nombre))
        conn.commit()
        return {"message": "Tarea material escolar creada. Lista para ser asignada."}, 201

    except Exception as e:
        if conn: conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
@tareas.route('/tareas-comanda', methods=['POST'])
def create_comanda_base():
    conn = None
    cursor = None
    try:

        conn = db.connect()
        cursor = conn.cursor()
        id_pictograma = 4952
        nombre = 'comanda'
        categoria = 'comanda'

        query = "INSERT INTO tarea (id_pictograma, nombre, categoria) VALUES (%s, %s, %s)"
        cursor.execute(query, (id_pictograma, nombre, categoria, ))     
        conn.commit()
        id_tarea = cursor.lastrowid
        query = "INSERT INTO comanda (id, id_pictograma, nombre) VALUES (%s, %s, %s)"
        cursor.execute(query, (id_tarea, id_pictograma, nombre))
        conn.commit()
        return {"message": "Tarea comanda creada. Lista para ser asignada."}, 201

    except Exception as e:
        if conn: conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/tareas-comanda/', methods=['DELETE'])
def delete_tarea_comanda():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        
        query = "DELETE FROM tarea WHERE categoria = 'comanda'"
        cursor.execute(query, )
        
        conn.commit()

        query = "DELETE FROM comanda WHERE id = 1"
        cursor.execute(query, )
        conn.commit()

        if cursor.rowcount == 0:
            return {"error": "No se encontró la tarea para eliminar"}, 404

        return {"message": "Tarea y todas sus dependencias eliminadas correctamente"}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

from datetime import datetime, timedelta

@tareas.route('/asignar-tarea', methods=['POST'])
def asignar_tarea_estudiante():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        tarea_id = data.get('id_tarea')
        estudiante_id = data.get('id_estudiante')
        profesor_id = data.get('id_profesor')
        f_inicio_str = data.get('fecha_inicio')
        f_fin_str = data.get('fecha_fin')

        f_inicio = datetime.strptime(f_inicio_str, '%Y-%m-%d')
        f_fin = datetime.strptime(f_fin_str, '%Y-%m-%d')

        conn = db.connect()
        cursor = conn.cursor()

        delta = (f_fin - f_inicio).days

    
        for i in range(delta + 1):
            fecha_actual = (f_inicio + timedelta(days=i)).strftime('%Y-%m-%d')

            #id, id_pictograma, nombre, categoria -> tarea 
            #id, usermame, etc -> estudiantes
            
            query = """
                INSERT IGNORE INTO tarea_estudiante (tarea_id, estudiante_id, fecha) 
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (tarea_id, estudiante_id, fecha_actual, ))
            conn.commit()
            
            

            if cursor.rowcount > 0: 
                query = "SELECT id FROM comanda WHERE nombre = 'comanda'"
                cursor.execute(query, )
                comanda_id = cursor.fetchone()['id']
                query = """INSERT IGNORE INTO estudiante_comanda (fecha, estudiante_id, comanda_id)
                        VALUES (%s, %s, %s)"""
                cursor.execute(query, (fecha_actual, estudiante_id, comanda_id))
                conn.commit()
                
                query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id, visitado) SELECT %s, %s, %s, id, FALSE FROM aulas"""
                cursor.execute(query, (tarea_id, estudiante_id, fecha_actual,))
                conn.commit()
            else: 
                return {"message": "Ha habido un error al asignar la tarea"}, 500

        # Obtenemos info para la notificación push (solo una notificación al final)
        query_info = """
            SELECT t.nombre, e.expo_push_token
            FROM tarea t
            JOIN estudiantes e ON e.id = %s
            WHERE t.id = %s
        """
        cursor.execute(query_info, (estudiante_id, tarea_id))
        info = cursor.fetchone()
        
        conn.commit()

        if info and info['expo_push_token']: 
            enviar_push(
                info['expo_push_token'],
                '¡NUEVAS TAREAS!',
                f"SE TE HAN ASIGNADO TAREAS DE: {info['nombre']} PARA VARIOS DÍAS"
            )
        
        return {
            "message": "Tareas diarias asignadas con éxito",
            "id_profesor": profesor_id
        }, 201

    except Exception as e:
        if conn: conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/tareas/<int:id_estudiante>', methods=['GET'])
#@jwt_required() Lo haremos mas adelante
def get_tareas_estudiante_fecha(id_estudiante):
    conn = None
    cursor = None
    try:
       
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 10, type=int)
        fecha_consulta = request.args.get('fecha') 

        conn = db.connect()
        cursor = conn.cursor()

        
        query = """
                    SELECT * FROM tarea AS t INNER JOIN tarea_estudiante AS te
                    ON t.id = te.tarea_id 
                    WHERE te.estudiante_id = %s AND te.fecha = %s AND te.material_asignado = 1
                    LIMIT %s OFFSET %s
                """

        cursor.execute(query, (id_estudiante, fecha_consulta, limit, offset))


        lista_tareas = cursor.fetchall()
    
        

        # 3. Obtener el total para la paginación
        query_count = """
            SELECT COUNT(*) as total 
            FROM tarea_estudiante 
            WHERE estudiante_id = %s 
              AND fecha = %s
        """
        cursor.execute(query_count, (id_estudiante, fecha_consulta))
        count_res = cursor.fetchone()

        return jsonify({
            "ok": True,
            "tareasEstudiante": lista_tareas,
            "count": count_res['total'],
            "offset": offset + limit
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/resumen-mensual/<int:id_estudiante>', methods=['GET'])
def get_resumen_mensual(id_estudiante):
    mes_buscado = request.args.get('mes')  
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        #
        query = """
            SELECT fecha, completado
            FROM tarea_estudiante
            WHERE estudiante_id = %s 
              AND DATE_FORMAT(fecha, '%%Y-%%m') = %s
              AND material_asignado = 1
        """
        cursor.execute(query, (id_estudiante, mes_buscado))
        tareas = cursor.fetchall()

        resumen_dias = {}
        for t in tareas:
            fecha_str = t['fecha'].strftime('%Y-%m-%d') if isinstance(t['fecha'], (datetime, date)) else str(t['fecha'])

            completado = bool(t['completado'])

            
            if fecha_str not in resumen_dias:
                resumen_dias[fecha_str] = {"todas_hechas": completado}
            else:
                
                if not completado:
                    resumen_dias[fecha_str]["todas_hechas"] = False

        return jsonify(resumen_dias), 200

    except Exception as e:
        print(f"Error: {e}")
        print(str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@tareas.route('/finalizar-tarea', methods=['POST'])
def finalizar_tarea():
   
    data = request.json
    tarea_id = data.get("tarea_id")
    estudiante_id = data.get("estudiante_id")
    fecha = data.get("fecha")

    if not all([tarea_id, estudiante_id, fecha]):
        return {"status": "error", "message": "Faltan parámetros"}, 400

    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        query = """UPDATE estudiantes SET puntos = puntos + 1 WHERE id = %s"""
        cursor.execute(query, (estudiante_id,))
        conn.commit()
        
        query_tarea = """
            UPDATE tarea_estudiante
            SET completado = 1
            WHERE tarea_id = %s
              AND estudiante_id = %s
              AND fecha = %s
        """
        cursor.execute(query_tarea, (tarea_id, estudiante_id, fecha))

        #obtenemos el id del administrador para la notificación push
        query_admin = """SELECT id FROM profesores WHERE tipo = 'admin' LIMIT 1"""
        cursor.execute(query_admin, )        
        admin = cursor.fetchone()
        admin_id = admin['id'] if admin else None

        conn.commit()
        #Buscamos el nombre del estudiante para la notificación push
        query = """SELECT username FROM estudiantes WHERE id = %s"""
        cursor.execute(query, (estudiante_id, ))
        estudiante = cursor.fetchone()
        
        #obtenemos info para la notificacion push (solo una notificación al final)
        query_info = """SELECT t.nombre, p.expo_push_token
            FROM tarea t
            JOIN profesores p ON p.id = %s
            WHERE t.id = %s"""
        cursor.execute(query_info, (admin_id, tarea_id))
        info = cursor.fetchone()
        if info and info['expo_push_token']:
            enviar_push(
                info['expo_push_token'],
                '¡TAREA FINALIZADA!',
                f"{estudiante['username']} HA FINALIZADO LA TAREA: {info['nombre']}"
            )
        if cursor.rowcount > 0:
            return {
                "status": "success",
                "message": "Tarea y visitas finalizadas correctamente"
            }, 200
        else:
            return {
                "status": "error",
                "message": "No se encontró ninguna tarea o visita con esos datos"
            }, 404
        
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error fatal al finalizar tarea: {e}")
        return {"status": "error", "message": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@tareas.route('/asignar-tarea-pedido', methods=['POST'])
def asignar_tarea_pedido():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        tarea_id = data.get('id_tarea')
        estudiante_id = data.get('id_estudiante')
        profesor_id = data.get('id_profesor')
        f_inicio_str = data.get('fecha_inicio')
        f_fin_str = data.get('fecha_fin')

        f_inicio = datetime.strptime(f_inicio_str, '%Y-%m-%d')
        f_fin = datetime.strptime(f_fin_str, '%Y-%m-%d')

        conn = db.connect()
        cursor = conn.cursor()

        delta = (f_fin - f_inicio).days

    
        for i in range(delta + 1):
            fecha_actual = (f_inicio + timedelta(days=i)).strftime('%Y-%m-%d')

            query = """
                INSERT IGNORE INTO tarea_estudiante (tarea_id, estudiante_id, fecha, material_asignado) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (tarea_id, estudiante_id, fecha_actual, False, ))
            conn.commit()
            

            # Si ya existia la tarea_estudiante (INSERT IGNORE), seguimos con el flujo.
            query = "SELECT id FROM pedido_material WHERE id = %s"
            cursor.execute(query, (tarea_id, ))
            pedido_material = cursor.fetchone()
            if not pedido_material:
                return {"message": "No existe un pedido_material asociado al id_tarea enviado"}, 400

            pedido_material_id = pedido_material['id']
            query = """INSERT IGNORE INTO estudiante_pedido_material (fecha, estudiante_id, pedido_material_id)
                    VALUES (%s, %s, %s)"""
            cursor.execute(query, (fecha_actual, estudiante_id, pedido_material_id))
            conn.commit()

            # Evita error 1062 si la relacion ya existe para este pedido/profesor/estudiante.
            query = """INSERT IGNORE INTO pedido_profesor_estudiante (chat_id, pedido_material_id, profesor_id, estudiante_id, fecha_asignacion) VALUES (UUID(), %s, %s, %s, %s)"""
            cursor.execute(query, (pedido_material_id, profesor_id, estudiante_id, fecha_actual))
            conn.commit()

        query_info = """
            SELECT expo_push_token
            FROM profesores WHERE id = %s
        """
        cursor.execute(query_info, (profesor_id,))
        info = cursor.fetchone()
        if info and info['expo_push_token']:
            enviar_push(
                info['expo_push_token'],
                '¡NUEVAS PETICIONES DE MATERIAL ESCOLAR!',
                f"TIENES PETICIONES DE MATERIAL ESCOLAR ASIGNA MATERIALES PARA QUE EL ESTUDIANTE PUEDA REALIZAR LA TAREA"
            )
        return {
            "message": "Tareas diarias de pedido material asignadas con éxito",
            "id_profesor": profesor_id
        }, 201

    except Exception as e:
        if conn: conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/tareas-peticion-profesor/<int:profesor_id>', methods=['GET'])
def get_tareas_peticion_profesor(profesor_id):
    conn = None
    cursor = None
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 10, type=int)
        fecha = request.args.get('fecha')
        print(f"fecha: {fecha}")
        conn = db.connect()
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT ppe.id, t.nombre, t.id_pictograma, t.categoria, e.username AS estudiante_nombre, te.fecha
            FROM tarea t
            JOIN tarea_estudiante te
                ON t.id = te.tarea_id
            JOIN estudiantes e
                ON e.id = te.estudiante_id
            JOIN pedido_material pm
                ON pm.id = t.id
            JOIN pedido_profesor_estudiante ppe
                ON ppe.pedido_material_id = pm.id
                AND ppe.estudiante_id = e.id
                AND ppe.fecha_asignacion = te.fecha
            WHERE ppe.profesor_id = %s
                AND te.fecha = %s
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (profesor_id, fecha, limit, offset))
        tareas_peticion = cursor.fetchall()

        query_count = """
            SELECT COUNT(DISTINCT t.id) AS total
            FROM tarea t
            JOIN tarea_estudiante te ON t.id = te.tarea_id
            JOIN estudiantes e ON e.id = te.estudiante_id
            JOIN pedido_material pm ON pm.id = t.id
            JOIN pedido_profesor_estudiante ppe ON ppe.pedido_material_id = pm.id AND ppe.estudiante_id = e.id
            WHERE ppe.profesor_id = %s AND te.material_asignado = 0 AND te.fecha = %s
        """
        cursor.execute(query_count, (profesor_id, fecha))
        count_res = cursor.fetchone()

        

        return jsonify({
            "ok": True,
            "tareas": tareas_peticion,
            "count": count_res['total'],
            "offset": offset + limit
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/asignar-material-profesor', methods=['POST'])
def asignar_material_profesor():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        data = request.get_json()


        materiales_seleccionados = data.get('materiales')
        id = data.get('id_tarea')
        fecha = date.today().strftime('%Y-%m-%d')
        profesor_id = data.get('profesor_id')
       

        query = """SELECT id FROM pedido_material LIMIT 1"""
        cursor.execute(query)
        tarea_id = cursor.fetchone()['id'] if cursor.rowcount > 0 else None


        if materiales_seleccionados is None or id is None or profesor_id is None:
            return {"error": "Faltan datos necesarios para asignar materiales"}, 400
        
        

        for material in materiales_seleccionados:
            material_id = material.get('materialId')
            cantidad = material.get('cantidad')
            query= """INSERT INTO profesor_material_pedido (material_id, profesor_id, pedido_id, fecha_asignacion, cantidad) VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(query, (material_id, profesor_id, tarea_id, fecha, cantidad))
            conn.commit()

            query = """UPDATE material_escolar SET cantidad = cantidad - %s WHERE id = %s"""
            cursor.execute(query, (cantidad, material_id))
            conn.commit()

        query = """SELECT e.id 
                FROM estudiantes e
                JOIN pedido_profesor_estudiante ppe ON ppe.estudiante_id = e.id 
            WHERE ppe.id = %s AND ppe.profesor_id = %s AND ppe.fecha_asignacion = %s"""
        cursor.execute(query, (id, profesor_id, fecha))
        estudiantes_afectados = cursor.fetchall()
        print(f"Estudiantes afectados: {estudiantes_afectados}")
        for estudiante in estudiantes_afectados:
            
            query = """SELECT id FROM aulas WHERE nombre = 'ALMACEN' LIMIT 1"""
            cursor.execute(query, )
            almacen_aula = cursor.fetchone()['id'] if cursor.rowcount > 0 else None
            query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id, visitado) VALUES (%s, %s, %s, %s, %s) """
            cursor.execute(query, (tarea_id, estudiante['id'], fecha, almacen_aula, False))
            conn.commit()

            query = """SELECT id_aula FROM profesor_aula WHERE id_profesor = %s LIMIT 1"""
            cursor.execute(query, (profesor_id, ))
            aula_id = cursor.fetchone()['id_aula'] if cursor.rowcount > 0 else None

            query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id, visitado) VALUES (%s, %s, %s, %s, %s)"""

            cursor.execute(query, (tarea_id, estudiante['id'], fecha, aula_id, False))
            conn.commit()
            
            query = """UPDATE tarea_estudiante 
                    SET material_asignado = 1 
                    WHERE estudiante_id = %s AND fecha = %s AND tarea_id = %s"""
            cursor.execute(query, (estudiante['id'], fecha, tarea_id))
            conn.commit()
            query_token = """SELECT expo_push_token FROM estudiantes WHERE id = %s"""
            cursor.execute(query_token, (estudiante['id'], ))
            info = cursor.fetchone()
            if info and info['expo_push_token']:
                enviar_push(
                    info['expo_push_token'],
                    '¡MATERIALES ASIGNADOS!',
                    f"SE TE HAN ASIGNADO LOS MATERIALES PARA REALIZAR LA TAREA DE HOY"
                )

        return {"message": "Materiales asignados correctamente"}, 200

    except Exception as e:
        if conn: conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tareas.route('/tarea-material-materiales', methods=['POST'])
def get_tarea_material_materiales():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        id_tarea_estudiante = data.get('id_tarea_estudiante')
        fecha = data.get('fecha')
        student_id = data.get('student_id')

        if not all([id_tarea_estudiante, fecha, student_id]):
            return {"error": "Faltan parámetros"}, 400

        conn = db.connect()
        cursor = conn.cursor()

        query = """
            SELECT me.id, me.nombre, pmp.cantidad, me.pictogramaId, me.forma, me.tamaño, me.color, me.imagen, me.video, pmp.seleccionado, pmp.profesor_id
            FROM material_escolar me
            JOIN profesor_material_pedido pmp ON pmp.material_id = me.id
            JOIN pedido_profesor_estudiante ppe ON ppe.pedido_material_id = pmp.pedido_id AND ppe.profesor_id = pmp.profesor_id AND ppe.estudiante_id = %s AND ppe.fecha_asignacion = %s
            JOIN tarea_estudiante te ON te.estudiante_id = ppe.estudiante_id AND te.fecha = ppe.fecha_asignacion AND te.tarea_id = %s
        """
        cursor.execute(query, (student_id, fecha, id_tarea_estudiante))
        materiales = cursor.fetchall()

        for m in materiales:
            m['color_voz'] = _color_name_from_hex(m.get('color'))

        print(materiales)

        return jsonify(materiales), 200

    except Exception as e:
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()