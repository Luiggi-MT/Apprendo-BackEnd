from flask import Blueprint, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from collections import defaultdict
import tempfile
from datetime import datetime
from db import Database

db = Database()
comandas = Blueprint('comandas', __name__)



db = Database()
comandas = Blueprint('comandas', __name__)

@comandas.route('/comanda/<int:tarea_id>', methods=['GET'])
def gestionar_comanda(tarea_id):
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        estudiante_id = request.args.get('estudiante_id')
        fecha = request.args.get('fecha')

        if not estudiante_id or not fecha:
            return {"message": "estudiante_id y fecha son necesarios"}, 400

        # --- 1. OBTENER AULAS ---
        query_aulas = """
            SELECT 
                a.id as id_visita,
                a.nombre AS nombre,
                va.visitado,
                p.foto AS foto_profesor,
                p.username AS nombre_profesor
            FROM visita_aula va
            INNER JOIN aulas a ON va.aula_id = a.id
            LEFT JOIN profesor_aula pa ON a.id = pa.id_aula
            LEFT JOIN profesores p ON pa.id_profesor = p.id
            WHERE va.tarea_id = %s
            AND va.estudiante_id = %s
            AND va.fecha = %s
            ORDER BY a.nombre ASC
        """
        cursor.execute(query_aulas, (tarea_id, estudiante_id, fecha))
        aulas = cursor.fetchall()

        # --- 2. OBTENER MENÚ ---
        query_menu = """
            SELECT p.id AS id_plato,
                   p.nombre,
                   p.id_pictograma,
                   p.categoria
            FROM platos p
            JOIN menu_plato mp ON p.id = mp.plato_id
        """
        cursor.execute(query_menu)
        platos_menu = cursor.fetchall()

        return jsonify({
            "aulas": aulas,
            "menu_del_dia": platos_menu
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@comandas.route('/comanda/menus', methods=['GET'])
def get_menus_con_cantidades():
    conn = None
    cursor = None

    try:
        conn = db.connect()
        cursor = conn.cursor()

        tarea_id = request.args.get('tarea_id')
        estudiante_id = request.args.get('estudiante_id')
        fecha = request.args.get('fecha')
        aula_id = request.args.get('aula_id')
        categoria = request.args.get('categoria', 'menu') 
        limit = int(request.args.get('limit', 3))
        offset = int(request.args.get('offset', 0))

        if not all([tarea_id, estudiante_id, fecha, aula_id]):
            return {"message": "Faltan parámetros"}, 400

        # Total de menús de la categoría (sin filtrar tachado)
        query_total = """
            SELECT COUNT(*) AS total
            FROM menu
            WHERE categoria = %s
        """
        cursor.execute(query_total, (categoria,))
        total = cursor.fetchone()['total']

        # Menús paginados
        query_menus = """
            SELECT id, descripcion, id_pictograma, tachado
            FROM menu
            WHERE categoria = %s
            ORDER BY descripcion ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query_menus, (categoria, limit, offset))
        menus_db = cursor.fetchall()

        if not menus_db:
            return {"menu": [], "limit": limit, "offset": offset, "total": total}, 200

        menus = []

        query_platos = """
            SELECT 
                p.id,
                p.nombre,
                p.id_pictograma,
                p.categoria,
                am.cantidad AS cantidad
            FROM menu_plato mp
            JOIN platos p ON mp.plato_id = p.id
            LEFT JOIN aula_menu am
                ON am.menu_id = mp.menu_id
                AND am.tarea_id = %s
                AND am.estudiante_id = %s
                AND am.fecha = %s
                AND am.aula_id = %s
            WHERE mp.menu_id = %s
        """

        for menu in menus_db:
            cursor.execute(query_platos, (
                tarea_id,
                estudiante_id,
                fecha,
                aula_id,
                menu['id']
            ))
            platos = cursor.fetchall()

            menus.append({
                "id": menu['id'],
                "descripcion": menu['descripcion'],
                "id_pictograma": menu['id_pictograma'],
                "tachado": bool(menu['tachado']), 
                "platos": platos
            })

        return {"menu": menus, "limit": limit, "offset": offset, "total": total}, 200

    except Exception as e:
        print("Error get_menus_con_cantidades:", e)
        return {"error": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@comandas.route('/comanda/menus/<string:search>')
def get_menus_con_cantidades_by_name(search):
    
    conn = None
    cursor = None

    try:
        conn = db.connect()
        cursor = conn.cursor()

        tarea_id = request.args.get('tarea_id')
        estudiante_id = request.args.get('estudiante_id')
        limit = int(request.args.get('limit', 3))
        offset = int(request.args.get('offset', 0))
        fecha = request.args.get('fecha')
        aula_id = request.args.get('aula_id')
        categoria = request.args.get('categoria', 'menu') 

        if not all([tarea_id, estudiante_id, fecha, aula_id]):
            return {"message": "Faltan parámetros"}, 400

        query_menus = """
            SELECT id, descripcion, id_pictograma, tachado
            FROM menu
            WHERE categoria = %s
            AND descripcion LIKE %s
            ORDER BY descripcion ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query_menus, (categoria, f"%{search}%", limit, offset))
        menus_db = cursor.fetchall()

        query = """SELECT COUNT(*) FROM menu WHERE categoria = %s AND descripcion LIKE %s"""
        cursor.execute(query, (categoria, f"%{search}%"))
        total = cursor.fetchone()[0]

        if not menus_db:
            return {"menu": [], "total": 0}, 200

        menus = []

        query_platos = """
            SELECT 
                p.id,
                p.nombre,
                p.id_pictograma,
                p.categoria,
                am.cantidad AS cantidad
            FROM menu_plato mp
            JOIN platos p ON mp.plato_id = p.id
            LEFT JOIN aula_menu am
                ON am.menu_id = mp.menu_id
                AND am.tarea_id = %s
                AND am.estudiante_id = %s
                AND am.fecha = %s
                AND am.aula_id = %s
            WHERE mp.menu_id = %s
        """

        for menu in menus_db:
            cursor.execute(query_platos, (
                tarea_id,
                estudiante_id,
                fecha,
                aula_id,
                menu['id']
            ))

            platos = cursor.fetchall()

            menus.append({
                "id": menu['id'],
                "descripcion": menu['descripcion'],
                "id_pictograma": menu['id_pictograma'],
                "tachado": bool(menu['tachado']),
                "platos": platos,
            })

        return {"menu": menus, "limit": limit, "offset": offset, "total": total}, 200

    except Exception as e:
        print("Error get_menus_con_cantidades_by_name:", e)
        return {"error": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@comandas.route('/comanda/guardar-visita', methods=['POST'])
def guardar_visita():
    data = request.json

    conn = None
    cursor = None

    try:
        conn = db.connect()
        cursor = conn.cursor()

        tarea_id = data['tarea_id']
        estudiante_id = data['estudiante_id']
        fecha = data['fecha']
        aula_id = data['aula_id']

        cursor.execute("""
            UPDATE visita_aula
            SET visitado = 1
            WHERE tarea_id = %s
              AND estudiante_id = %s
              AND fecha = %s
              AND aula_id = %s
        """, (tarea_id, estudiante_id, fecha, aula_id))

        conn.commit()
        return {"message": "Comanda guardada correctamente"}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error guardar_visita:", e)
        return {"error": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@comandas.route('/comanda/pedido', methods=['POST'])
def set_cantidad_pedido():
    data = request.json

    conn = None
    cursor = None

    try:
        conn = db.connect()
        cursor = conn.cursor()

        tarea_id = data['tarea_id']
        estudiante_id = data['estudiante_id']
        fecha = data['fecha']
        aula_id = data['aula_id']
        id_menu = data['id_menu']
        id_plato = data['id_plato']
        cantidad = data['cantidad']

        cursor.execute("""
            INSERT INTO aula_menu
            (tarea_id, estudiante_id, fecha, aula_id, menu_id, cantidad)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                cantidad = VALUES(cantidad)
        """, (
            tarea_id,
            estudiante_id,
            fecha,
            aula_id,
            id_menu,
            cantidad
        ))

        conn.commit()
        return {"message": "Cantidad actualizada correctamente"}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error set_cantidad_pedido:", e)
        return {"error": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@comandas.route('/comanda/detallada', methods=['GET'])
def get_comanda_detallada():
    fecha = request.args.get('fecha')
    id_aula = request.args.get('id_aula')

    if not fecha or not id_aula:
        return jsonify({"error": "Faltan parámetros: fecha o id_aula"}), 400

    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        # 1️⃣ Obtenemos los menús y cantidades de esa aula en esa fecha
        query_menus = """
            SELECT am.menu_id, am.cantidad AS cantidad_menu, m.descripcion, m.id_pictograma
            FROM aula_menu am
            JOIN menu m ON am.menu_id = m.id
            JOIN visita_aula va
              ON va.tarea_id = am.tarea_id
             AND va.estudiante_id = am.estudiante_id
             AND va.fecha = am.fecha
             AND va.aula_id = am.aula_id
            WHERE am.aula_id = %s AND am.fecha = %s
        """
        cursor.execute(query_menus, (id_aula, fecha))
        menus_db = cursor.fetchall()

        if not menus_db:
            return jsonify([]), 200

        comanda_result = []

        # 2️⃣ Para cada menú obtenemos los platos
        query_platos = """
            SELECT p.id AS id_plato, p.nombre, p.categoria, p.id_pictograma, am.cantidad AS cantidad
            FROM menu_plato mp
            JOIN platos p ON mp.plato_id = p.id
            JOIN aula_menu am ON mp.menu_id = am.menu_id
            WHERE mp.menu_id = %s AND am.aula_id = %s AND am.fecha = %s
        """

        for menu in menus_db:
            cursor.execute(query_platos, (menu['menu_id'], id_aula, fecha))
            platos = cursor.fetchall()

            comanda_result.append({
                "nombre_aula": f"AULA {id_aula}",
                "menu": menu["descripcion"],
                "id_menu": menu["menu_id"],
                "id_pictograma_menu": menu["id_pictograma"],
                "platos": platos
            })

        return jsonify(comanda_result), 200

    except Exception as e:
        print(f"Error get_comanda_detallada: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@comandas.route('/comanda/aula-fecha', methods=['GET'])
def get_aulas_por_fecha():
    fecha = request.args.get('fecha')
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))

    if not fecha:
        return {"error": "Falta el parámetro 'fecha'"}, 400

    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        # Obtenemos aulas que tienen visita_aula en esa fecha
        query = """
            SELECT DISTINCT
                a.id,
                a.nombre AS nombre_aula
            FROM aulas a
            JOIN visita_aula va ON va.aula_id = a.id
            WHERE va.fecha = %s
            ORDER BY a.nombre ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (fecha, limit, offset))
        aulas = cursor.fetchall()

        return {"aulas": aulas}, 200

    except Exception as e:
        print(f"Error get_aulas_por_fecha: {e}")
        return {"error": str(e)}, 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@comandas.route('/comanda/descargar-pdf', methods=['GET'])
def descargar_comanda_pdf():
    fecha = request.args.get('fecha')

    if not fecha:
        return jsonify({"error": "Fecha requerida"}), 400

    conn = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        # Consulta adaptada a tu estructura: aula_menu -> menu -> menu_plato -> platos
        query = """
            SELECT 
                a.id AS aula_id,
                a.nombre AS nombre_aula,
                m.id AS menu_id,
                m.descripcion AS menu,
                m.categoria AS categoria_menu,
                m.id_pictograma AS id_pictograma_menu,
                p.id AS id_plato,
                p.nombre AS nombre_plato,
                p.categoria,
                p.id_pictograma AS id_pictograma_plato,
                am.cantidad
            FROM aula_menu am
            JOIN aulas a ON am.aula_id = a.id
            JOIN menu m ON am.menu_id = m.id
            JOIN menu_plato mp ON m.id = mp.menu_id
            JOIN platos p ON mp.plato_id = p.id
            WHERE am.fecha = %s AND am.cantidad > 0
            ORDER BY 
                a.nombre ASC,
                CASE
                    WHEN m.categoria = 'menu' THEN 0
                    WHEN m.categoria = 'postre' THEN 1
                    ELSE 2
                END,
                m.descripcion ASC,
                p.categoria ASC
        """
        cursor.execute(query, (fecha,))
        filas = cursor.fetchall()

        if not filas:
            return jsonify({"error": "No hay comandas para esa fecha"}), 404

        # Agrupamos por aula, categoría y menú
        aulas = defaultdict(lambda: {
            "menu": defaultdict(list),
            "postre": defaultdict(list),
            "otros": defaultdict(list),
        })
        for fila in filas:
            aula = fila["nombre_aula"]
            menu = fila["menu"].strip()
            categoria_menu = (fila.get("categoria_menu") or "").strip().lower()
            if categoria_menu not in ("menu", "postre"):
                categoria_menu = "otros"

            aulas[aula][categoria_menu][menu].append({
                "plato": fila["nombre_plato"],
                "categoria": fila["categoria"],
                "cantidad": fila["cantidad"],
                "id_pictograma": fila["id_pictograma_plato"]
            })

        # Generamos PDF
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf = canvas.Canvas(tmp.name, pagesize=A4)
        width, height = A4
        y = height - 40

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, y, f"Comanda del día {fecha}")
        y -= 40

        pdf.setFont("Helvetica", 11)

        for aula, categorias in aulas.items():
            y -= 20
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(40, y, aula)
            pdf.setFont("Helvetica", 11)
            y -= 15

            for tipo in ("menu", "postre", "otros"):
                menus = categorias[tipo]
                if not menus:
                    continue

                if tipo == "postre":
                    postres_agrupados = defaultdict(int)
                    for _, platos in menus.items():
                        for plato in platos:
                            nombre_postre = plato["plato"]
                            postres_agrupados[nombre_postre] += int(plato["cantidad"])

                    pdf.setFont("Helvetica-Bold", 11)
                    pdf.drawString(50, y, "Postres:")
                    pdf.setFont("Helvetica", 11)
                    y -= 14

                    for nombre, cantidad in sorted(postres_agrupados.items()):
                        pdf.drawString(60, y, f"- {nombre}: {cantidad}")
                        y -= 14
                        if y < 40:
                            pdf.showPage()
                            y = height - 40

                    y -= 20

                    if y < 40:
                        pdf.showPage()
                        y = height - 40

                    continue

                for menu, platos in menus.items():
                    pdf.setFont("Helvetica-Bold", 11)
                    if tipo == "menu":
                        pdf.drawString(50, y, f"Menú: {menu}")
                    else:
                        pdf.drawString(50, y, f"Elemento: {menu}")
                    pdf.setFont("Helvetica", 11)
                    y -= 14

                    for plato in platos:
                        pdf.drawString(
                            60, y,
                            f"- {plato['plato']} ({plato['categoria']}): {plato['cantidad']}"
                        )
                        y -= 14
                        if y < 40:
                            pdf.showPage()
                            y = height - 40

                    y -= 10  # espacio entre menús
            y -= 10  # espacio entre aulas

        pdf.save()

        return send_file(
            tmp.name,
            as_attachment=True,
            download_name=f"comanda_{fecha}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("Error PDF:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()
