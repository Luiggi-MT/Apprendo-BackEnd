from flask import Blueprint, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
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

    estudiante_id = request.args.get('estudiante_id')
    fecha = request.args.get('fecha')

    if not estudiante_id or not fecha:
        return {"message": "estudiante_id y fecha son necesarios"}, 400

    # __ 1. Comprobar si existen las aulas y en caso contrario insertarlas

    query = """SELECT id, nombre FROM aulas WHERE UPPER(nombre) != 'ALMACEN'"""

    aulas_db = db.fetch_query(query)

    query = """SELECT aula_id as id FROM visita_aula WHERE tarea_id = %s AND estudiante_id = %s AND fecha = %s"""

    aula_visitada_db = db.fetch_query(query, (tarea_id, estudiante_id, fecha))

    for aula in aulas_db:
        if not any(av['id'] == aula['id'] for av in aula_visitada_db):
            insert_query = """INSERT INTO visita_aula (tarea_id, estudiante_id, fecha, aula_id, visitado) VALUES (%s, %s, %s, %s, FALSE)"""
            try:
                db.execute_query(
                    insert_query, (tarea_id, estudiante_id, fecha, aula['id']))
            except Exception as e:
                return {"message": f"Ha habido un error al insertar la visita al aula {aula['nombre']}"}, 500

    # --- 2. OBTENER AULAS ---
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
        AND UPPER(a.nombre) != 'ALMACEN'
        ORDER BY a.nombre ASC
        """

    aulas = db.fetch_query(query_aulas, (tarea_id, estudiante_id, fecha))

    # --- 1. OBTENER MENÚ ---
    query_menu = """
        SELECT p.id AS id_plato,
                p.nombre,
                p.id_pictograma,
                p.categoria
        FROM platos p
        JOIN menu_plato mp ON p.id = mp.plato_id
        """
    platos_menu = db.fetch_query(query_menu)

    return jsonify({
        "aulas": aulas,
        "menu_del_dia": platos_menu
    }), 200


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
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
            AND UPPER(a.nombre) != 'ALMACEN'
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
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
            AND UPPER(a.nombre) != 'ALMACEN'
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
        c = canvas.Canvas(tmp.name, pagesize=A4)
        width, height = A4

        # ── Paleta de colores ──────────────────────────────────────
        # azul oscuro — cabecera página
        COLOR_HEADER_BG = colors.HexColor("#1E3A5F")
        # azul medio  — cabecera aula
        COLOR_AULA_BG = colors.HexColor("#2E86C1")
        COLOR_MENU_BG = colors.HexColor("#D6EAF8")   # azul claro  — fila menú
        COLOR_POSTRE_BG = colors.HexColor(
            "#FDEBD0")   # naranja claro— fila postre
        # gris muy claro — filas alternas
        COLOR_ROW_ALT = colors.HexColor("#F4F6F7")
        COLOR_TEXT_LIGHT = colors.white
        COLOR_TEXT_DARK = colors.HexColor("#1C2833")
        COLOR_ACCENT = colors.HexColor("#FF8C42")   # naranja acento

        MARGIN_L = 20 * mm
        MARGIN_R = width - 20 * mm
        PAGE_W = MARGIN_R - MARGIN_L

        def check_page(y_pos, needed=20):
            if y_pos < 30 * mm + needed:
                c.showPage()
                return draw_page_header()
            return y_pos

        def draw_page_header():
            # Banda superior azul oscuro
            c.setFillColor(COLOR_HEADER_BG)
            c.rect(0, height - 18 * mm, width, 18 * mm, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.setFont("Helvetica-Bold", 13)
            fecha_fmt = datetime.strptime(
                fecha, "%Y-%m-%d").strftime("%d / %m / %Y")
            c.drawString(MARGIN_L, height - 12 * mm,
                         f"COMANDA DEL DÍA  {fecha_fmt}")
            c.setFont("Helvetica", 9)
            c.drawRightString(MARGIN_R, height - 12 * mm,
                              f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            # Línea acento naranja
            c.setStrokeColor(COLOR_ACCENT)
            c.setLineWidth(2)
            c.line(0, height - 18 * mm, width, height - 18 * mm)
            return height - 26 * mm   # y de inicio

        def draw_aula_header(y_pos, nombre_aula):
            h = 9 * mm
            c.setFillColor(COLOR_AULA_BG)
            c.rect(MARGIN_L - 2, y_pos - h + 3,
                   PAGE_W + 4, h, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT_LIGHT)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(MARGIN_L + 3, y_pos - h + 6,
                         f"🏫  {nombre_aula.upper()}")
            return y_pos - h - 3

        def draw_section_label(y_pos, label, bg_color):
            h = 7 * mm
            c.setFillColor(bg_color)
            c.rect(MARGIN_L + 5, y_pos - h + 2,
                   PAGE_W - 5, h, fill=1, stroke=0)
            c.setFillColor(COLOR_TEXT_DARK)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN_L + 10, y_pos - h + 5, label)
            return y_pos - h - 2

        def draw_row(y_pos, texto, cantidad, alt=False):
            h = 6.5 * mm
            bg = COLOR_ROW_ALT if alt else colors.white
            c.setFillColor(bg)
            c.rect(MARGIN_L + 5, y_pos - h + 2,
                   PAGE_W - 5, h, fill=1, stroke=0)
            # borde izquierdo acento
            c.setStrokeColor(COLOR_ACCENT)
            c.setLineWidth(1)
            c.line(MARGIN_L + 5, y_pos - h + 2, MARGIN_L + 5, y_pos + 2)
            c.setFillColor(COLOR_TEXT_DARK)
            c.setFont("Helvetica", 9)
            c.drawString(MARGIN_L + 10, y_pos - h + 5, texto)
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(MARGIN_R - 5, y_pos - h + 5, str(cantidad))
            return y_pos - h - 1

        def draw_divider(y_pos):
            c.setStrokeColor(colors.HexColor("#BDC3C7"))
            c.setLineWidth(0.5)
            c.line(MARGIN_L, y_pos, MARGIN_R, y_pos)
            return y_pos - 4

        # ── Render ────────────────────────────────────────────────
        y = draw_page_header()

        for nombre_aula, categorias in aulas.items():
            y = check_page(y, needed=40 * mm)
            y = draw_aula_header(y, nombre_aula)

            # — Menús —
            menus_cat = categorias.get("menu", {})
            if menus_cat:
                y = check_page(y, 20)
                y = draw_section_label(y, "MENÚS", COLOR_MENU_BG)
                alt = False
                for menu_nombre, platos in menus_cat.items():
                    y = check_page(y, 10)
                    c.setFillColor(COLOR_MENU_BG)
                    c.setFont("Helvetica-Bold", 9)
                    c.rect(MARGIN_L + 5, y - 5 * mm + 2,
                           PAGE_W - 5, 5 * mm, fill=1, stroke=0)
                    c.setFillColor(COLOR_TEXT_DARK)
                    c.drawString(MARGIN_L + 10, y - 5 * mm + 5, menu_nombre)
                    y -= 5 * mm + 1
                    for plato in platos:
                        y = check_page(y, 8)
                        label = f"{plato['plato']}"
                        if plato.get('categoria'):
                            label += f"  ({plato['categoria']})"
                        y = draw_row(y, label, plato['cantidad'], alt)
                        alt = not alt
                    y -= 2

            # — Postres —
            postres_cat = categorias.get("postre", {})
            if postres_cat:
                postres_agrupados = defaultdict(int)
                for _, platos in postres_cat.items():
                    for plato in platos:
                        postres_agrupados[plato["plato"]
                                          ] += int(plato["cantidad"])

                y = check_page(y, 20)
                y = draw_section_label(y, "POSTRES", COLOR_POSTRE_BG)
                alt = False
                for nombre, cantidad in sorted(postres_agrupados.items()):
                    y = check_page(y, 8)
                    y = draw_row(y, nombre, cantidad, alt)
                    alt = not alt
                y -= 2

            y = draw_divider(y)
            y -= 4

        # Pie de página en la última página
        c.setFillColor(colors.HexColor("#BDC3C7"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 20, "Cole — Sistema de gestión escolar")

        c.save()

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
