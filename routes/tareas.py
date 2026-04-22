from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
from db import Database
from const import LIMIT
from routes.notificaciones import enviar_push
from routes.materialEscolar import _color_name_from_hex
from flask_jwt_extended import jwt_required, get_jwt

db = Database()

tareas = Blueprint('tareas', __name__)


@tareas.route('/tareas')
def get_tareas():

    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', LIMIT))

    query = f"""SELECT id, id_pictograma, nombre, categoria
                FROM tarea
                WHERE nombre != 'pedido material'
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
    print("Asignando tarea a estudiante...")
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

        query = """
                INSERT INTO tarea_estudiante (tarea_id, estudiante_id, fecha)
                VALUES (%s, %s, %s)
                """
        try:
            filas = db.execute_query(
                query, (tarea_id, estudiante_id, fecha_actual, ))
            print(
                f"Filas insertadas: {filas} para tarea_id: {tarea_id}, estudiante_id: {estudiante_id}, fecha: {fecha_actual}")
        except Exception as e:
            return {"message": "Ha habido un error al asignar la tarea"}, 500

        # Comprobamos si la tarea se ha insertado correctamente
        if filas > 0:
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
              AND material_asignado = 1
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
    fecha = data.get('fecha')

    print(
        f"Recibida solicitud para asignar tarea pedido con estudiante_id: {estudiante_id}, profesor_id: {profesor_id}, fecha: {fecha}")

    if not all([estudiante_id, profesor_id, fecha]):
        return {"message": "Faltan datos necesarios para asignar la tarea"}, 400

    query = """SELECT id FROM tarea WHERE categoria = 'material_escolar'"""

    try:
        tarea_id_db = db.fetch_query(query, fetchone=True)
    except Exception as e:
        print(f"Error al buscar la tarea de material escolar: {e}")
        return {"message": "Ha habido un error al buscar la tarea de material escolar"}, 500

    # Comprobamos si ya existe la tarea para el estudiante
    query = f"""SELECT tarea_id as id FROM tarea_estudiante WHERE tarea_id = %s AND estudiante_id = %s AND fecha = %s"""
    try:
        tarea_estudiante = db.fetch_query(
            query, (tarea_id_db['id'], estudiante_id, fecha), fetchone=True)
    except Exception as e:
        print(f"Error al buscar la tarea_estudiante: {e}")
        return {"message": "Ha habido un error al buscar la tarea_estudiante"}, 500

    if not tarea_estudiante:
        query = """
                INSERT INTO tarea_estudiante (tarea_id, estudiante_id, fecha)
                VALUES (%s, %s, %s)
                """
        try:
            db.execute_query(
                query, (tarea_id_db['id'], estudiante_id, fecha))
        except Exception as e:
            print(
                f"Error al asignar la tarea de material escolar al estudiante: {e}")
            return {"message": "Ha habido un error al asignar la tarea"}, 500

    query = f"""SELECT profesor_id, fecha FROM pedido WHERE profesor_id = %s AND fecha = %s"""
    try:
        pedido_material = db.fetch_query(
            query, (profesor_id, fecha), fetchone=True)
    except Exception as e:
        print(f"Error al buscar el pedido_material asociado a la tarea: {e}")
        return {"message": "Ha habido un error al buscar el pedido_material asociado a la tarea"}, 500

    if not pedido_material:
        return {"message": "No existe un pedido_material asociado al id_tarea enviado"}, 400

    pedido_material_id = tarea_id_db['id']
    query = """INSERT INTO estudiante_pedido_material (fecha, estudiante_id, pedido_material_id)
                VALUES (%s, %s, %s)"""
    try:
        db.execute_query(
            query, (fecha, estudiante_id, pedido_material_id))
    except Exception as e:
        return {"message": "Ha habido un error al asignar el pedido_material al estudiante"}, 500

    # Evita error 1062 si la relacion ya existe para este pedido/profesor/estudiante.
    query = """INSERT INTO pedido_profesor_estudiante (chat_id, pedido_material_id, profesor_id, estudiante_id, fecha_asignacion) VALUES (UUID(), %s, %s, %s, %s)"""
    try:
        db.execute_query(query, (pedido_material_id,
                                 profesor_id, estudiante_id, fecha))
    except Exception as e:
        return {"message": "Ha habido un error al asignar el pedido_material al profesor"},

    query = f"""UPDATE pedido 
                SET estudiante_id = %s
            WHERE profesor_id = %s AND fecha = %s"""
    try:
        db.execute_query(query, (estudiante_id, profesor_id, fecha))
    except Exception as e:
        return {"message": "Ha habido un error al actualizar el pedido con el estudiante"}, 500

    query_info = """
                SELECT expo_push_token
                FROM profesores WHERE id = %s
                """
    try:
        info = db.fetch_query(query_info, (profesor_id, ), fetchone=True)
    except Exception as e:
        return {"message": "Ha habido un error al buscar el token del profesor para la notificación"}, 500

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

    # __ 1. Comprobamos si existe la solicitud para modificarla
    query = """SELECT profesor_id, fecha FROM pedido WHERE profesor_id = %s AND fecha = %s"""
    try:
        pedido = db.fetch_query(query, (profesor_id, fecha), fetchone=True)
    except Exception as e:
        print(f"Error al buscar el pedido para el profesor: {e}")
        return {"message": "Ha habido un error al buscar el pedido para el profesor"}, 500

    # __ 2. Insertamos la petición del profesor para ese día
    if not pedido:
        query = """INSERT INTO pedido (profesor_id, fecha) VALUES (%s, %s)"""
        try:
            db.execute_query(query, (profesor_id, fecha))
        except Exception as e:
            print(f"Error al crear pedido para el profesor: {e}")
            return {"message": "Ha habido un error al crear el pedido para el profesor"}, 500

    for material in materiales_seleccionados:
        material_id = material.get('materialId')
        cantidad_nueva = material.get('cantidad')

        # Ver si ya existe una asignación previa
        query = """SELECT cantidad FROM profesor_material_pedido
                    WHERE material_id = %s AND profesor_id = %s AND fecha = %s"""
        try:
            existente = db.fetch_query(
                query, (material_id, profesor_id, fecha), fetchone=True)
        except Exception as e:
            print(f"Error al buscar la asignación previa del material: {e}")
            return {"message": "Ha habido un error al buscar la asignación previa del material"}, 500

        if existente:
            cantidad_anterior = existente['cantidad']
            diferencia = cantidad_anterior - cantidad_nueva  # positivo = devolver al stock
            # Restaurar stock: devolver lo anterior y descontar lo nuevo
            query = """UPDATE material_escolar SET cantidad = cantidad + %s WHERE id = %s"""
            try:
                db.execute_query(query, (diferencia, material_id))
            except Exception as e:
                print(f"Error al actualizar el stock del material: {e}")
                return {"message": "Ha habido un error al actualizar el stock del material"}, 500

            if cantidad_nueva > 0:
                query = """UPDATE profesor_material_pedido SET cantidad = %s
                            WHERE material_id = %s AND profesor_id = %s AND fecha = %s
                        """
                try:
                    db.execute_query(
                        query, (cantidad_nueva, material_id, profesor_id, fecha))
                except Exception as e:
                    print(
                        f"Error al actualizar la asignación del material: {e}")
                    return {"message": "Ha habido un error al actualizar la asignación del material"}, 500
            else:
                # Si la cantidad es 0, eliminar la fila de la asignación
                query = """DELETE FROM profesor_material_pedido
                            WHERE material_id = %s AND profesor_id = %s AND fecha = %s
                        """
                try:
                    db.execute_query(
                        query, (material_id, profesor_id, fecha))
                except Exception as e:
                    print(f"Error al eliminar la asignación del material: {e}")
                    return {"message": "Ha habido un error al eliminar la asignación del material"}, 500
        else:
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
            profesores = db.fetch_query(
                query)
        except Exception as e:
            print(f"Error al buscar los profesores administradores: {e}")
            return {"message": "Ha habido un error al buscar los profesores administradores"}, 500

        query = """SELECT username FROM profesores WHERE id = %s"""
        try:
            profesor_info = db.fetch_query(
                query, (profesor_id, ), fetchone=True)
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

    query = """
            SELECT me.id, me.nombre, pmp.cantidad, me.pictogramaId, me.forma, me.tamaño, me.color, me.imagen, me.video, pmp.seleccionado, pmp.profesor_id
            FROM material_escolar me
            JOIN profesor_material_pedido pmp ON pmp.material_id = me.id
            JOIN pedido_profesor_estudiante ppe ON ppe.profesor_id = pmp.profesor_id AND ppe.estudiante_id = %s AND ppe.fecha_asignacion = %s
            JOIN tarea_estudiante te ON te.estudiante_id = ppe.estudiante_id AND te.fecha = ppe.fecha_asignacion AND te.tarea_id = %s
        """
    try:
        materiales = db.fetch_query(
            query, (student_id, fecha, id_tarea_estudiante))
    except Exception as e:
        print(f"Error al obtener los materiales para la tarea: {e}")
        return {"message": "Ha habido un error al obtener los materiales para la tarea"},

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
