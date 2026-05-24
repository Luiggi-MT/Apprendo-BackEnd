import asyncio
from datetime import datetime, timedelta, date, timezone
from flask import Blueprint, request, jsonify, send_file
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from db import Database
from mongo import MongoDB
from const import LIMIT
from routes.notificaciones import enviar_push
from routes.materialEscolar import _color_name_from_hex
from flask_jwt_extended import jwt_required, get_jwt
import uuid
import io
from datetime import datetime, date, timedelta, timezone
from collections import defaultdict

# Imports necesarios de ReportLab para gráficos vectoriales nativos
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

db = Database()

tareas = Blueprint('tareas', __name__)


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Fallback defensivo por si hay un event loop activo en el contexto.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@tareas.route('/tareas')
def get_tareas():

    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', LIMIT))

    query = f"""SELECT id, id_pictograma, nombre, categoria
                FROM tarea
                ORDER BY nombre
                LIMIT %s OFFSET %s"""

    try:
        tareas_db = db.fetch_query(query, (limit, offset, ))
    except Exception as e:
        print(str(e))
        return {'error': str(e)}, 500

    tareas_list = []

    for tarea in tareas_db:
        tareas_list.append({
            'id': tarea['id'],
            'id_pictograma': tarea['id_pictograma'],
            'nombre': tarea['nombre'],
            'categoria': tarea['categoria'],
        })
    query_count = "SELECT COUNT(*) FROM tarea"
    try:
        count_row = db.fetch_query(query_count, fetchone=True)
    except Exception as e:
        print(str(e))
        return {'error': str(e)}, 500

    count = count_row[0] if isinstance(
        count_row, tuple) else list(count_row.values())[0]

    return {
        'tareas': tareas_list,
        'offset': offset + limit,
        'count': count,
    }, 200


@tareas.route('/tareas/buscar')
def buscar_tareas():
    conn = None
    cursor = None
    try:
        nombre = request.args.get('nombre', '')
        if not nombre:
            return {'error': 'El nombre es necesario'}, 400
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
        except ValueError:
            limit = LIMIT

        conn = db.connect()
        cursor = conn.cursor()
        query = f"""SELECT id, id_pictograma, nombre, categoria FROM tarea WHERE nombre LIKE %s ORDER BY nombre LIMIT %s OFFSET %s"""
        cursor.execute(query, ('%' + nombre + '%', limit, offset))
        tareas = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) FROM tarea WHERE nombre LIKE %s", ('%' + nombre + '%',))
        count_row = cursor.fetchone()
        count = count_row[0] if isinstance(
            count_row, tuple) else list(count_row.values())[0]

        tareas_list = [{'id': t['id'], 'id_pictograma': t['id_pictograma'],
                        'nombre': t['nombre'], 'categoria': t['categoria']} for t in tareas]

        return {'tareas': tareas_list, 'offset': offset + limit, 'count': count}, 200
    except Exception as e:
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
            return {'exists': False}, 200

        return {'exists': True}, 200

    except Exception as e:
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
        if conn:
            conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
        if conn:
            conn.rollback()
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@tareas.route('/tareas-comanda/', methods=['DELETE'])
def delete_tarea_comanda():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        query = "DELETE FROM tarea WHERE categoria = 'comanda'"
        cursor.execute(query)
        tareas_eliminadas = cursor.rowcount
        conn.commit()

        query = "DELETE FROM comanda WHERE id = 1"
        cursor.execute(query)
        conn.commit()

        if tareas_eliminadas == 0:
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


@tareas.route('/asignar-tarea', methods=['POST'])
@jwt_required()
def asignar_tarea_estudiante():

    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403

    data = request.get_json()
    tarea_id = data.get('id_tarea')
    estudiante_id = data.get('id_estudiante')
    profesor_id = data.get('id_profesor')
    f_inicio_str = data.get('fecha_inicio')
    f_fin_str = data.get('fecha_fin')

    f_inicio = datetime.strptime(f_inicio_str, '%Y-%m-%d')
    f_fin = datetime.strptime(f_fin_str, '%Y-%m-%d')

    delta = (f_fin - f_inicio).days

    for i in range(delta + 1):
        fecha_actual = (f_inicio + timedelta(days=i)).strftime('%Y-%m-%d')
        chat_session_id = str(uuid.uuid4())
        query = """
                INSERT INTO tarea_estudiante (tarea_id, estudiante_id, fecha, chat_session_id)
                VALUES (%s, %s, %s, %s)
                """
        try:
            filas = db.execute_query(
                query, (tarea_id, estudiante_id, fecha_actual, chat_session_id))
            print(
                f"Filas insertadas: {filas} para tarea_id: {tarea_id}, estudiante_id: {estudiante_id}, fecha: {fecha_actual}")
        except Exception as e:
            return {"message": "Ha habido un error al asignar la tarea"}, 500

        # Comprobamos si la tarea se ha insertado correctamente
        if filas > 0:
            try:
                query = """SELECT nombre FROM tarea WHERE id = %s"""
                tarea_nombre = db.fetch_query(
                    query, (tarea_id, ), fetchone=True)['nombre']
                if tarea_nombre != "comanda":
                    mongo = MongoDB()
                    chat_collection = mongo.get_collection("chat_sessions")
                    chat_collection.insert_one({
                        "_id": chat_session_id,
                        "tarea_id": tarea_id,
                        "estudiante_id": estudiante_id,
                        "profesor_id": profesor_id,
                        "fecha": fecha_actual,
                        "status": "active",
                        "created_at": datetime.now(timezone.utc),
                        "closed_at": None
                    })
            except Exception as e:
                print(f"Error al crear la sesión de chat en MongoDB: {e}")
                return {"message": "Ha habido un error al crear la sesión de chat para la tarea"}, 500

            query = "SELECT id FROM comanda WHERE nombre = 'comanda'"
            try:
                comanda = db.fetch_query(query, fetchone=True)
            except Exception as e:
                return {"message": "Ha habido un error al buscar la comanda asociada a la tarea"}, 500
            if comanda:
                comanda_id = comanda['id']
                query = """INSERT INTO estudiante_comanda (fecha, estudiante_id, comanda_id)
                        VALUES (%s, %s, %s)"""
                try:
                    db.execute_query(
                        query, (fecha_actual, estudiante_id, comanda_id))
                except Exception as e:
                    return {"message": "Ha habido un error al asignar la comanda al estudiante"}, 500

            else:
                return {"message": "Ha habido un error al asignar la tarea"}, 500

        # Obtenemos info para la notificación push (solo una notificación al final)
        query_info = """
            SELECT t.nombre, e.expo_push_token
            FROM tarea t
            JOIN estudiantes e ON e.id = %s
            WHERE t.id = %s
        """

        try:
            info = db.fetch_query(
                query_info, (estudiante_id, tarea_id, ), fetchone=True)
        except Exception as e:
            return {"message": "Ha habido un error al buscar el token del estudiante para la notificación"}, 500

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


@tareas.route('/tareas/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def get_tareas_estudiante_fecha(id_estudiante):

    claims = get_jwt()
    if claims.get('tipo') != 'estudiante' and claims.get('tipo') != 'admin' and claims.get('tipo') != 'profesor':
        return {"error": "Acceso no autorizado"}, 403

    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', LIMIT, type=int)
    fecha_consulta = request.args.get('fecha')

    query = """
                SELECT * FROM tarea AS t INNER JOIN tarea_estudiante AS te
                ON t.id = te.tarea_id
                WHERE te.estudiante_id = %s AND te.fecha = %s
                LIMIT %s OFFSET %s
            """
    try:
        lista_tareas = db.fetch_query(
            query, (id_estudiante, fecha_consulta, limit, offset))
    except Exception as e:
        print(f"Error al consultar tareas del estudiante: {e}")
        return {"message": "Ha habido un error al consultar las tareas del estudiante"}, 500

    # 3. Obtener el total para la paginación
    query_count = """
                    SELECT COUNT(*) as total
                    FROM tarea_estudiante
                    WHERE estudiante_id = %s
                    AND fecha = %s
                """
    try:
        count_res = db.fetch_query(
            query_count, (id_estudiante, fecha_consulta), fetchone=True)
    except Exception as e:
        print(f"Error al contar tareas del estudiante: {e}")
        return {"message": "Ha habido un error al contar las tareas del estudiante"}, 500

    return jsonify({
        "ok": True,
        "tareasEstudiante": lista_tareas,
        "count": count_res['total'],
        "offset": offset + limit
    }), 200


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
        """
        cursor.execute(query, (id_estudiante, mes_buscado))
        tareas = cursor.fetchall()

        resumen_dias = {}
        for t in tareas:
            fecha_str = t['fecha'].strftime(
                '%Y-%m-%d') if isinstance(t['fecha'], (datetime, date)) else str(t['fecha'])

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
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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

        query_chat_session = """
            SELECT chat_session_id
            FROM tarea_estudiante
            WHERE tarea_id = %s
              AND estudiante_id = %s
              AND fecha = %s
            LIMIT 1
        """
        cursor.execute(query_chat_session, (tarea_id, estudiante_id, fecha))
        chat_session_row = cursor.fetchone()
        chat_session_id = (
            chat_session_row['chat_session_id']
            if chat_session_row and chat_session_row.get('chat_session_id')
            else None
        )

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
        query = """SELECT t.nombre FROM tarea t JOIN tarea_estudiante te ON t.id = te.tarea_id
                   WHERE te.tarea_id = %s AND te.estudiante_id = %s AND te.fecha = %s"""
        try:
            tarea_info = db.fetch_query(
                query, (tarea_id, estudiante_id, fecha), fetchone=True)
            tarea_nombre = tarea_info['nombre'] if tarea_info else 'la tarea'
        except Exception as e:
            tarea_nombre = ""

        if tarea_nombre != "comanda" and cursor.rowcount > 0 and chat_session_id:
            try:
                mongo = MongoDB()
                chat_collection = mongo.get_collection("chat_sessions")
                _run_async(chat_collection.update_one(
                    {"_id": chat_session_id},
                    {
                        "$set": {
                            "status": "closed",
                            "closed_at": datetime.now(timezone.utc)
                        }
                    }
                ))
            except Exception as e:
                print(f"Error al cerrar la sesión de chat en MongoDB: {e}")
                return {"status": "error", "message": "La tarea se actualizó pero no se pudo cerrar la sesión de chat"}, 500

        # obtenemos el id del administrador para la notificación push
        query_admin = """SELECT id FROM profesores WHERE tipo = 'admin' LIMIT 1"""
        cursor.execute(query_admin, )
        admin = cursor.fetchone()
        admin_id = admin['id'] if admin else None

        conn.commit()
        # Buscamos el nombre del estudiante para la notificación push
        query = """SELECT username FROM estudiantes WHERE id = %s"""
        cursor.execute(query, (estudiante_id, ))
        estudiante = cursor.fetchone()

        # obtenemos info para la notificacion push (solo una notificación al final)
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
@jwt_required()
def asignar_tarea_pedido():

    if get_jwt().get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403

    data = request.get_json()
    estudiante_id = data.get('id_estudiante')
    profesor_id = data.get('id_profesor')
    fecha_inicio_str = data.get('fecha_inicio')
    fecha_fin_str = data.get('fecha_fin')

    if not all([estudiante_id, profesor_id, fecha_inicio_str, fecha_fin_str]):
        return {"message": "Faltan datos necesarios para asignar la tarea"}, 400

    f_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
    f_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')

    delta = (f_fin - f_inicio).days

    query = """SELECT id FROM tarea WHERE categoria = 'material_escolar'"""

    try:
        tarea_id_db = db.fetch_query(query, fetchone=True)
    except Exception as e:
        print(f"Error al buscar la tarea de material escolar: {e}")
        return {"message": "Ha habido un error al buscar la tarea de material escolar"}, 500

    if not tarea_id_db:
        return {"message": "No se encontró ninguna tarea con la categoría 'material_escolar'"}, 404

    chat_session_id = str(uuid.uuid4())

    query = """SELECT id FROM aulas WHERE nombre = 'ALMACEN'"""
    try:
        aula_id_db = db.fetch_query(query, fetchone=True)
    except Exception as e:
        print(f"Error al buscar el aula 'ALMACEN': {e}")
        return {"message": "Ha habido un error al buscar el aula 'ALMACEN'"}, 500

    if not aula_id_db:
        return {"message": "No se encontró el aula 'ALMACEN'"}, 404

    almacen_id = aula_id_db['id']

    query = """SELECT id_aula FROM profesor_aula WHERE id_profesor = %s"""
    try:
        profesor_aula = db.fetch_query(query, (profesor_id, ), fetchone=True)
    except Exception as e:
        print(f"Error al buscar el aula del profesor: {e}")
        return {"message": "Ha habido un error al buscar el aula del profesor"}, 500
    profesor_aula_id = profesor_aula['id_aula'] if profesor_aula else None

    # Bucle diario para insertar las tareas del estudiante
    for i in range(delta + 1):
        # CORREGIDO: Se cambia days=1 por days=i para que avance el calendario en cada iteración
        fecha_actual = (f_inicio + timedelta(days=i)).strftime('%Y-%m-%d')
        query = """
                INSERT INTO tarea_estudiante (tarea_id, estudiante_id, fecha, chat_session_id, id_profesor)
                VALUES (%s, %s, %s, %s, %s)
                """
        try:
            db.execute_query(
                query, (tarea_id_db['id'], estudiante_id, fecha_actual, chat_session_id, profesor_id))
        except Exception as e:
            print(
                f"Error al asignar la tarea de material escolar al estudiante: {e}")
            return {"message": "Ha habido un error al asignar la tarea"}, 500

        query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id)
                   VALUES (%s, %s, %s, %s)"""
        try:
            db.execute_query(
                query, (tarea_id_db['id'], estudiante_id, fecha_actual, almacen_id))
            db.execute_query(
                query, (tarea_id_db['id'], estudiante_id, fecha_actual, profesor_aula_id))
        except Exception as e:
            print(f"Error al asignar la visita al aula: {e}")
            return {"message": "Ha habido un error al asignar la visita al aula"}, 500

    query = """SELECT id FROM profesores WHERE tipo = 'admin'"""
    try:
        admin = db.fetch_query(query, fetchone=True)
    except Exception as e:
        print(f"Error al buscar el identificador del administrador: {e}")
        return {"message": "Ha habido un problema a la hora de crear el chat"}, 500

    admin_id = admin['id'] if admin else None

    # CORREGIDO: Eliminado '_run_async' para operar de forma síncrona nativa con pymongo
    try:
        mongo = MongoDB()
        chat_collection = mongo.get_collection("chat_sessions")
        chat_collection.update_one(
            {"_id": chat_session_id},
            {"$set": {
                "tarea_id": tarea_id_db['id'],
                "estudiante_id": estudiante_id,
                "profesor_id": admin_id,
                "fecha": f_inicio.strftime('%Y-%m-%d'),
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "closed_at": None
            }},
            upsert=True
        )
    except Exception as e:
        print(f"Error al crear/actualizar la sesión de chat en MongoDB: {e}")
        return {"message": "Ha habido un error al crear la sesión de chat para la tarea"}, 500

    # CORREGIDO: Query parametrizada de manera segura cambiando f-string por %s y solucionada la variable 'fecha'
    query_update_pedido = """UPDATE pedido 
                             SET estudiante_id = %s
                             WHERE profesor_id = %s AND fecha = %s"""
    try:
        db.execute_query(query_update_pedido, (estudiante_id,
                         profesor_id, fecha_inicio_str))
    except Exception as e:
        print(f"Error al actualizar el pedido: {e}")
        return {"message": "Ha habido un error al actualizar el pedido con el estudiante"}, 500

    query_info = """
                SELECT expo_push_token
                FROM estudiantes WHERE id = %s
                """
    try:
        info = db.fetch_query(query_info, (estudiante_id, ), fetchone=True)
    except Exception as e:
        return {"message": "Ha habido un error al buscar el token del profesor para la notificación"}, 500

    if info and info['expo_push_token']:
        enviar_push(
            info['expo_push_token'],
            '¡NUEVAS PETICIONES DE MATERIAL ESCOLAR!',
            "TIENES UNA TAREA DE PEDIDO DE MATERIAL PARA HACER"
        )

    return {
        "message": "Tareas diarias de pedido material asignadas con éxito",
        "id_profesor": profesor_id
    }, 201


@tareas.route('/tareas-peticion-profesor/<int:profesor_id>', methods=['GET'])
def get_tareas_peticion_profesor(profesor_id):

    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 10, type=int)
    fecha = request.args.get('fecha')

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
    try:
        # Solo para probar la consulta y evitar errores antes de ejecutar el fetchall
        tareas_peticion = db.fetch_query(
            query, (profesor_id, fecha, limit, offset))
    except Exception as e:
        print(f"Error al obtener las tareas de petición para el profesor: {e}")
        return {"message": "Ha habido un error al obtener las tareas de petición para el profesor"}, 500

    query_count = """
            SELECT COUNT(DISTINCT t.id) AS total
            FROM tarea t
            JOIN tarea_estudiante te ON t.id = te.tarea_id
            JOIN estudiantes e ON e.id = te.estudiante_id
            JOIN pedido_material pm ON pm.id = t.id
            JOIN pedido_profesor_estudiante ppe ON ppe.pedido_material_id = pm.id AND ppe.estudiante_id = e.id
            WHERE ppe.profesor_id = %s AND te.material_asignado = 0 AND te.fecha = %s
        """
    try:
        count_res = db.fetch_query(
            query_count, (profesor_id, fecha), fetchone=True)
    except Exception as e:
        print(f"Error al contar las tareas de petición para el profesor: {e}")
        return {"message": "Ha habido un error al contar las tareas de petición para el profesor"}, 500

    return jsonify({
        "ok": True,
        "tareas": tareas_peticion,
        "count": count_res['total'],
        "offset": offset + limit
    }), 200


@tareas.route('/profesor-material-asignado/<int:profesor_id>/<int:tarea_id>', methods=['GET'])
def get_profesor_material_asignado(profesor_id, tarea_id):
    conn = None
    cursor = None
    try:
        fecha = request.args.get('fecha', date.today().strftime('%Y-%m-%d'))
        conn = db.connect()
        cursor = conn.cursor()
        query = """
            SELECT me.id AS material_id, me.nombre, me.pictogramaId, pmp.cantidad
            FROM profesor_material_pedido pmp
            JOIN material_escolar me ON me.id = pmp.material_id
            WHERE pmp.profesor_id = %s AND pmp.pedido_id = %s AND pmp.fecha_asignacion = %s
        """
        cursor.execute(query, (profesor_id, tarea_id, fecha))
        materiales = cursor.fetchall()
        return jsonify({"ok": True, "materiales": materiales}), 200
    except Exception as e:
        print(f"Error get_profesor_material_asignado: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@tareas.route('/asignar-material-profesor', methods=['POST'])
def asignar_material_profesor():

    data = request.get_json()

    materiales_seleccionados = data.get('materiales')
    fecha = date.today().strftime('%Y-%m-%d')
    profesor_id = data.get('profesor_id')

    if materiales_seleccionados is None or profesor_id is None:
        return {"error": "Faltan datos necesarios para asignar materiales"}, 400

    # __ 1. Insertamos la petición del profesor para ese día
    query = """INSERT INTO pedido (profesor_id, fecha) VALUES (%s, %s)"""
    try:
        db.execute_query(query, (profesor_id, fecha))
    except Exception as e:
        print(f"Error al crear pedido para el profesor: {e}")
        return {"message": "Ha habido un error al crear el pedido para el profesor"}, 500

    for material in materiales_seleccionados:
        material_id = material.get('materialId')
        cantidad_nueva = material.get('cantidad')

        query = """INSERT INTO profesor_material_pedido (material_id, profesor_id, fecha, cantidad)
                           VALUES (%s, %s, %s, %s)"""
        try:

            db.execute_query(
                query, (material_id, profesor_id, fecha, cantidad_nueva))
        except Exception as e:
            print(f"Error al insertar la asignación del material: {e}")
            return {"message": "Ha habido un error al insertar la asignación del material"}, 500

        query = """UPDATE material_escolar SET cantidad = cantidad - %s WHERE id = %s"""
        try:
            db.execute_query(query, (cantidad_nueva, material_id))

        except Exception as e:
            print(f"Error al actualizar el stock del material: {e}")
            return {"message": "Ha habido un error al actualizar el stock del material"}, 500

    query = """SELECT id
                FROM profesores
                WHERE tipo = 'admin'"""
    try:
        profesores = db.fetch_query(query)
    except Exception as e:
        print(f"Error al buscar los profesores administradores: {e}")
        return {"message": "Ha habido un error al buscar los profesores administradores"}, 500

    query = """SELECT username FROM profesores WHERE id = %s"""

    try:
        profesor_info = db.fetch_query(query, (profesor_id, ), fetchone=True)
    except Exception as e:
        print(
            f"Error al buscar el nombre del profesor para la notificación: {e}")
        return {"message": "Ha habido un error al buscar el nombre del profesor para la notificación"}, 500

    nombre_profesor = profesor_info['username'] if profesor_info else 'un profesor'

    for profesor in profesores:

        query_token = """SELECT expo_push_token FROM profesores WHERE id = %s"""
        try:
            info = db.fetch_query(
                query_token, (profesor['id'], ), fetchone=True)
        except Exception as e:
            print(
                f"Error al buscar el token del profesor para la notificación: {e}")
            return {"message": "Ha habido un error al obtener el token de notificación"}, 500

        if info and info['expo_push_token']:
            enviar_push(
                info['expo_push_token'],
                '¡NUEVA PETICIÓN DE MATERIAL!',
                f"SE HAN ASIGNADO MATERIALES POR EL PROFESOR {nombre_profesor} PARA EL DÍA {fecha}"
            )

    return {"message": "Materiales asignados correctamente"}, 200


@tareas.route('/tarea-material-materiales', methods=['POST'])
def get_tarea_material_materiales():

    data = request.get_json()
    id_tarea_estudiante = data.get('id_tarea_estudiante')
    fecha = data.get('fecha')
    student_id = data.get('student_id')

    if not all([id_tarea_estudiante, fecha, student_id]):
        return {"error": "Faltan parámetros"}, 400

    print(
        f"Recibida petición para obtener materiales de la tarea. id_tarea_estudiante: {id_tarea_estudiante}, fecha: {fecha}, student_id: {student_id}")
    query = """
            SELECT me.id, me.nombre, pmp.cantidad, me.pictogramaId, me.forma, me.tamaño, me.color, me.imagen, me.video, pmp.seleccionado, pmp.profesor_id
            FROM material_escolar me
            JOIN profesor_material_pedido pmp ON pmp.material_id = me.id
            JOIN tarea_estudiante te ON te.id_profesor = pmp.profesor_id
            WHERE te.estudiante_id = %s AND te.fecha = %s AND te.tarea_id = %s
        """
    try:
        materiales = db.fetch_query(
            query, (student_id, fecha, id_tarea_estudiante))
    except Exception as e:
        print(f"Error al obtener los materiales para la tarea: {e}")
        return {"message": "Ha habido un error al obtener los materiales para la tarea"}, 500
    print(materiales)
    for m in materiales:
        m['color_voz'] = _color_name_from_hex(m.get('color'))

    return jsonify(materiales), 200


@tareas.route('/tareas-material-escolar', methods=['GET'])
def get_tarea_material_escolar():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        query = """SELECT id FROM tarea WHERE categoria = 'material_escolar' LIMIT 1"""
        cursor.execute(query, )
        tarea_material_escolar = cursor.fetchone()

        if tarea_material_escolar:
            return {"exists": True}, 200
        else:
            return {"exists": False}, 200

    except Exception as e:
        print(str(e))
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@tareas.route('/tareas-materiales-escolares/<int:profesor_id>', methods=['GET'])
def get_tareas_materiales_escolares(profesor_id):

    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 3, type=int)
    fecha = request.args.get('fecha')

    query = """
            SELECT DISTINCT t.id, t.nombre, t.id_pictograma, t.categoria,
                            e.username AS estudiante_nombre, e.foto, te.fecha
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
    db.fetch_query(query, (profesor_id, fecha, limit, offset), fetchall=True)

    query_count = """
            SELECT COUNT(DISTINCT t.id) AS total
            FROM tarea t
            JOIN tarea_estudiante te ON t.id = te.tarea_id
            JOIN estudiantes e ON e.id = te.estudiante_id
            JOIN pedido_material pm ON pm.id = t.id
            JOIN pedido_profesor_estudiante ppe ON ppe.pedido_material_id = pm.id AND ppe.estudiante_id = e.id
            WHERE ppe.profesor_id = %s AND te.fecha = %s
        """
    db.fetch_query(query_count, (profesor_id, fecha), fetchone=True)

    return jsonify({
        "ok": True,
        "tareas": tareas_peticion,
        "count": count_res['total'],
        "offset": offset + limit
    }), 200


@tareas.route('/tareas-estudiante/<int:id>', methods=['GET'])
@jwt_required()
def get_tareas_estudiante(id):

    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403
    data = request.args
    offset = data.get('offset', 0, type=int)
    limit = data.get('limit', LIMIT, type=int)
    query = """SELECT t.nombre, t.id_pictograma, te.fecha, te.nota, te.completado, te.tarea_id as id 
                FROM tarea_estudiante te JOIN tarea t ON t.id = te.tarea_id
                WHERE te.estudiante_id = %s 
                ORDER BY t.nombre
                LIMIT %s OFFSET %s"""
    try:
        tareas_estudiante = db.fetch_query(query, (id, limit, offset))
    except Exception as e:
        return {"message": "Ha habido un error al obtener las tareas del estudiante"}, 500
    query_count = """SELECT COUNT(*) as total FROM tarea_estudiante te JOIN tarea t ON t.id = te.tarea_id
                    WHERE te.estudiante_id = %s"""
    try:
        count_res = db.fetch_query(query_count, (id, ), fetchone=True)
    except Exception as e:
        return {"message": "Ha habido un error al contar las tareas del estudiante"}, 500
    return jsonify({
        "ok": True,
        "tareasEstudiante": tareas_estudiante,
        "count": count_res['total'],
        "offset": offset + limit
    }), 200


@tareas.route('/tareas-estudiante/<int:id>/nota', methods=['POST'])
@jwt_required()
def asignar_nota_tarea_estudiante(id):

    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no autorizado"}, 403

    data = request.json
    tarea_id = data.get('tarea_id')
    nota = data.get('nota')
    print(data)
    if tarea_id is None or nota is None:
        return {"message": "Faltan datos necesarios para asignar la nota"}, 400
    print(
        f"Asignando nota {nota} a tarea_id {tarea_id} del estudiante_id {id}")
    query = """UPDATE tarea_estudiante SET nota = %s WHERE estudiante_id = %s AND tarea_id = %s"""
    try:
        db.execute_query(query, (nota, id, tarea_id))
    except Exception as e:
        return {"message": "Ha habido un error al asignar la nota a la tarea del estudiante"}, 500
    return {"message": "Nota asignada correctamente"}, 200


@tareas.route('/estudiantes/<int:student_id>/resumen-pdf', methods=['GET'])
@jwt_required()
def get_resumen_pdf(student_id):
    # Verificación de roles (Solo el Administrador tiene acceso)
    claims = get_jwt()
    if claims.get('tipo') != 'admin':
        return {"error": "Acceso no authorized"}, 403

    # 1. Obtener la información del estudiante
    query_estudiante = "SELECT username FROM estudiantes WHERE id = %s"
    try:
        estudiante = db.fetch_query(
            query_estudiante, (student_id,), fetchone=True)
        if not estudiante:
            return {"message": "Estudiante no encontrado"}, 404
        nombre_estudiante = estudiante['username']
    except Exception as e:
        print(f"Error al buscar estudiante para el PDF: {e}")
        return {"message": "Error al consultar los datos del estudiante"}, 500

    # 2. Obtener las estadísticas de sus tareas
    query_estadisticas = """
        SELECT t.nombre, te.fecha, te.nota, te.completado 
        FROM tarea_estudiante te 
        JOIN tarea t ON t.id = te.tarea_id
        WHERE te.estudiante_id = %s 
        ORDER BY te.fecha ASC
    """
    try:
        tareas_estudiante = db.fetch_query(query_estadisticas, (student_id,))
    except Exception as e:
        print(f"Error al obtener estadísticas para el PDF: {e}")
        return {"message": "Error al consultar las estadísticas de las tareas"}, 500

    # 3. Procesar datos generales para el reporte
    total_tareas = len(tareas_estudiante)
    tareas_completadas = sum(1 for t in tareas_estudiante if t['completado'])

    # Evitamos mezclar tipos mapeando las notas de la BD (Decimal) explícitamente a floats
    notas_validas = [float(t['nota'])
                     for t in tareas_estudiante if t['nota'] is not None]
    promedio_notas = round(
        sum(notas_validas) / len(notas_validas), 2) if notas_validas else "Sin notas"
    porcentaje_exito = round(
        (tareas_completadas / total_tareas) * 100, 1) if total_tareas > 0 else 0

    # -------------------------------------------------------------------------
    # PROCESAMIENTO DE DATOS PARA EL GRÁFICO MENSUAL (Conversión Defensiva a float)
    # -------------------------------------------------------------------------
    datos_mensuales = defaultdict(lambda: {"total": 0, "notas": []})

    for t in tareas_estudiante:
        f = t['fecha']
        fecha_obj = f if isinstance(f, (datetime, date)) else datetime.strptime(
            str(f), '%Y-%m-%d').date()
        clave_mes = fecha_obj.strftime('%m/%Y')

        datos_mensuales[clave_mes]["total"] += 1
        if t['nota'] is not None:
            datos_mensuales[clave_mes]["notas"].append(float(t['nota']))

    meses_ordenados = sorted(datos_mensuales.keys(
    ), key=lambda x: datetime.strptime(x, '%m/%Y'))

    eje_x_meses = meses_ordenados if meses_ordenados else ["Sin datos"]
    serie_volumen = []
    serie_puntuacion = []

    for mes in meses_ordenados:
        serie_volumen.append(datos_mensuales[mes]["total"])
        notas_mes = datos_mensuales[mes]["notas"]
        media_mes = round(sum(notas_mes) / len(notas_mes),
                          1) if notas_mes else 0.0
        serie_puntuacion.append(media_mes)

    if not serie_volumen:
        serie_volumen = [0]
        serie_puntuacion = [0]

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DEL DOCUMENTO PDF TRABAJANDO EN MEMORIA
    # -------------------------------------------------------------------------
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PDFTitle', parent=styles['Heading1'], fontSize=24, leading=28,
        textColor=colors.HexColor("#1A365D"), spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'PDFSubtitle', parent=styles['Normal'], fontSize=12, leading=16,
        textColor=colors.HexColor("#4A5568"), spaceAfter=15
    )
    cell_style = ParagraphStyle(
        'PDFTableCell', parent=styles['Normal'], fontSize=10, leading=13
    )
    header_table_style = ParagraphStyle(
        'PDFTableHeader', parent=styles['Normal'], fontSize=11, leading=14,
        textColor=colors.white, fontName="Helvetica-Bold"
    )

    story = []

    # Título y metadatos
    story.append(Paragraph("Reporte de Rendimiento Académico", title_style))
    story.append(Paragraph(f"<b>Estudiante:</b> {nombre_estudiante}<br/>"
                           f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y')}", subtitle_style))
    story.append(Spacer(1, 10))

    # Tabla Resumen Global
    resumen_data = [
        [Paragraph("<b>Métrica</b>", cell_style),
         Paragraph("<b>Valor</b>", cell_style)],
        [Paragraph("Total de Tareas Asignadas", cell_style),
         Paragraph(str(total_tareas), cell_style)],
        [Paragraph("Tareas Completadas con Éxito", cell_style),
         Paragraph(str(tareas_completadas), cell_style)],
        [Paragraph("Porcentaje de Cumplimiento", cell_style),
         Paragraph(f"{porcentaje_exito}%", cell_style)],
        [Paragraph("Nota Promedio General", cell_style),
         Paragraph(str(promedio_notas), cell_style)]
    ]
    tabla_resumen = Table(resumen_data, colWidths=[250, 150])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#E2E8F0")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 20))

    # -------------------------------------------------------------------------
    # RENDERIZADO DEL GRÁFICO VECTORIAL DE REPORTLAB (Sin mezclar tipos)
    # -------------------------------------------------------------------------
    story.append(Paragraph(
        "<b>Evolución Mensual de Tareas y Calificaciones</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    dibujo = Drawing(480, 200)

    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 25
    chart.height = 140
    chart.width = 400

    # Asignamos las series limpias de floats
    chart.data = [serie_volumen, serie_puntuacion]
    chart.categoryAxis.categoryNames = eje_x_meses
    chart.categoryAxis.labels.fontSize = 9
    chart.categoryAxis.labels.dy = -10

    chart.valueAxis.valueMin = 0
    max_valor_detectado = max(max(serie_volumen), max(
        serie_puntuacion)) if total_tareas > 0 else 10
    chart.valueAxis.valueMax = max(max_valor_detectado + 2, 10)
    chart.valueAxis.valueStep = 2
    chart.valueAxis.labels.fontSize = 9

    # Paleta de colores para las barras
    chart.bars[0].fillColor = colors.HexColor("#4299E1")  # Volumen (Azul)
    chart.bars[1].fillColor = colors.HexColor(
        "#ED8936")  # Rendimiento (Naranja)
    chart.barSpacing = 3
    chart.groupSpacing = 10

    dibujo.add(chart)
    dibujo.add(String(60, 180, "■ Total Tareas Asignadas",
               fontSize=9, fillColor=colors.HexColor("#4299E1")))
    dibujo.add(String(220, 180, "■ Nota Promedio del Mes",
               fontSize=9, fillColor=colors.HexColor("#ED8936")))

    story.append(dibujo)
    story.append(Spacer(1, 20))

    # -------------------------------------------------------------------------
    # HISTÓRICO DETALLADO (Últimas tareas arriba)
    # -------------------------------------------------------------------------
    story.append(
        Paragraph("<b>Historial Detallado de Tareas</b>", styles['Heading2']))
    story.append(Spacer(1, 8))

    tabla_tareas_data = [[
        Paragraph("Tarea", header_table_style),
        Paragraph("Fecha", header_table_style),
        Paragraph("Estado", header_table_style),
        Paragraph("Nota", header_table_style)
    ]]

    # El reversed asegura que las tareas más recientes queden arriba del todo
    for t in reversed(tareas_estudiante):
        fecha_formateada = t['fecha'].strftime(
            '%d/%m/%Y') if isinstance(t['fecha'], (datetime, date)) else str(t['fecha'])
        estado = "Completada" if t['completado'] else "Pendiente"
        nota_str = str(t['nota']) if t['nota'] is not None else "-"

        tabla_tareas_data.append([
            Paragraph(t['nombre'], cell_style),
            Paragraph(fecha_formateada, cell_style),
            Paragraph(estado, cell_style),
            Paragraph(nota_str, cell_style)
        ])

    tabla_historial = Table(tabla_tareas_data, colWidths=[200, 100, 110, 100])
    tabla_historial.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F7FAFC")]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))

    story.append(tabla_historial)

    # Compilación final del PDF
    doc.build(story)
    buffer.seek(0)

    # Devuelve el Stream binario listo para consumirse en el front
    return send_file(
        buffer,
        as_attachment=False,
        mimetype='application/pdf',
        download_name=f"resumen_{student_id}.pdf"
    )
