from flask import Blueprint, request, jsonify
from flask import send_file
from db import Database
import os
import base64
import uuid
import traceback
import tempfile
import colorsys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from const import LIMIT

db = Database()
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MATERIAL_ESCOLAR_FOLDER = os.getenv(
    'MATERIAL_ESCOLAR_PATH',
    os.path.join(SERVER_ROOT, 'media', 'materialEscolar')
)

material_escolar = Blueprint('material_escolar', __name__)


def _hex_to_rgb(hex_color: str):
    if not isinstance(hex_color, str):
        return None
    value = hex_color.strip().lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    elif len(value) == 5:
        # Normaliza entradas incompletas tipo #FFD6D -> #FFD6DD
        value = value + value[-1]
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _color_name_from_hex(color_value: str) -> str:
    rgb = _hex_to_rgb(color_value)
    if not rgb:
        return color_value if color_value else 'Sin color'

    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    h_deg = h * 360.0

    # Colores acromaticos
    if v <= 0.12:
        return 'Negro'
    if s <= 0.12:
        if v >= 0.92:
            return 'Blanco'
        return 'Gris'

    # Colores cromaticos por rango de tono
    if h_deg < 15 or h_deg >= 345:
        # Rojos muy claros y poco saturados se perciben como rosa/pastel
        if s < 0.35 and v > 0.75:
            return 'Rosa'
        return 'Rojo'
    if h_deg < 40:
        # Tono anaranjado/ocres
        if v < 0.55:
            return 'Marron'
        return 'Naranja'
    if h_deg < 70:
        return 'Amarillo'
    if h_deg < 170:
        return 'Verde'
    if h_deg < 200:
        return 'Cian'
    if h_deg < 255:
        return 'Azul'
    if h_deg < 320:
        return 'Morado'
    return 'Rosa'


def _save_base64_file(data_uri: str, subfolder: str, extension: str) -> str:
    if not data_uri or ',' not in data_uri:
        raise ValueError('Formato de archivo inválido')

    header, encoded = data_uri.split(',', 1)
    if not encoded or encoded.lower() in ('null', 'none'):
        raise ValueError('El archivo está vacío o es inválido')

    raw = base64.b64decode(encoded, validate=True)
    if not raw:
        raise ValueError('No se pudo decodificar el archivo')

    folder = os.path.join(MATERIAL_ESCOLAR_FOLDER, subfolder)
    os.makedirs(folder, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{extension}"
    filepath = os.path.join(folder, filename)
    with open(filepath, 'wb') as f:
        f.write(raw)
    return f"media/materialEscolar/{subfolder}/{filename}"


@material_escolar.route('/materiales-escolares', methods=['POST'])
def create_material_escolar():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        color = data.get('color')
        pictograma_id = data.get('pictogramaId')
        cantidad = data.get('cantidad')
        forma = data.get('forma')
        tamaño = data.get('tamaño')
        imagen = data.get('imagen')
        video = data.get('video')  

        
        if not all([nombre, color, pictograma_id, cantidad, forma, tamaño, imagen, video]):
            return jsonify({'error': 'Faltan campos requeridos'}), 400

        imagen_path = _save_base64_file(imagen, 'imagenes', 'jpg')
        video_path  = _save_base64_file(video, 'videos', 'mp4') 

        conn = db.connect()
        cursor = conn.cursor()
        query = """
            INSERT INTO material_escolar
                (nombre, color, pictogramaId, cantidad, forma, tamaño, imagen, video)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        cursor.execute(query, (nombre, color, pictograma_id, cantidad, forma, tamaño, imagen_path, video_path))
        row = cursor.fetchone()
        if isinstance(row, dict):
            new_id = row.get('id')
        elif isinstance(row, (tuple, list)) and len(row) > 0:
            new_id = row[0]
        else:
            new_id = None

        if new_id is None:
            # Fallback for connectors/backends where RETURNING is not available.
            new_id = cursor.lastrowid

        conn.commit()

        return jsonify({'message': 'Material escolar creado exitosamente', 'id': new_id}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Error al crear material escolar: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al crear material escolar'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@material_escolar.route('/materiales-escolares', methods=['GET'])
def get_materiales_escolares(): 
    conn = None
    cursor = None
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', LIMIT))

        if offset < 0: offset = 0
        if limit <= 0: limit = LIMIT
    except ValueError:
        offset = 0
        limit = LIMIT
    try: 

        conn = db.connect()
        cursor = conn.cursor()
        query = """
            SELECT id, nombre, pictogramaId, cantidad
            FROM material_escolar
            ORDER BY nombre
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, offset))
        material_db = cursor.fetchall()

        if not material_db:
            return {'message': 'No se encontraron materiales escolares'}, 404
        
        query_count = "SELECT COUNT(*) AS total FROM material_escolar"
        cursor.execute(query_count)
        total_count = cursor.fetchone()['total'] if cursor.rowcount > 0 else 0

        materiales = []
        for material in material_db:
            materiales.append({
                'id': material['id'],
                'nombre': material['nombre'],
                'pictogramaId': material['pictogramaId'],
                'cantidad': material['cantidad']
            })

        print(materiales)
        return jsonify({'materialesEscolares': materiales, 'offset': offset + limit, 'count':  total_count}), 200
    except Exception as e:
        print(f"Error al obtener materiales escolares: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al obtener materiales escolares'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@material_escolar.route('/materiales-escolares/<string:name>', methods=['GET'])
def get_materiales_escolares_by_name(name):
    conn = None
    cursor = None
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', LIMIT))

        if offset < 0: offset = 0
        if limit <= 0: limit = LIMIT
    except ValueError:
        offset = 0
        limit = LIMIT
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = """
            SELECT id, nombre, pictogramaId, cantidad
            FROM material_escolar
            WHERE nombre LIKE %s
            ORDER BY nombre
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (f'%{name}%', limit, offset))
        material_db = cursor.fetchall()

        if not material_db:
            return {'message': 'No se encontraron materiales escolares con ese nombre'}, 404
        
        query_count = "SELECT COUNT(*) AS total FROM material_escolar WHERE nombre LIKE %s"
        cursor.execute(query_count, (f'%{name}%',))
        total_count = cursor.fetchone()['total'] if cursor.rowcount > 0 else 0
        materiales = []
        for material in material_db:
            materiales.append({
                'id': material['id'],
                'nombre': material['nombre'],
                'pictogramaId': material['pictogramaId'],
                'cantidad': material['cantidad']
            })

        print(materiales)
        return jsonify({'materialesEscolares': materiales, 'offset': offset + limit, 'count': total_count}), 200
    except Exception as e:
        print(f"Error al obtener materiales escolares por nombre: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al obtener materiales escolares por nombre'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@material_escolar.route('/materiales-escolares/id/<int:material_id>', methods=['GET'])
def get_material_escolar_by_id(material_id):
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = """
            SELECT id, nombre, color, pictogramaId, cantidad, forma, tamaño, imagen, video
            FROM material_escolar
            WHERE id = %s
            LIMIT 1
        """
        cursor.execute(query, (material_id,))
        material = cursor.fetchone()

        if not material:
            return jsonify({'error': 'Material escolar no encontrado'}), 404

        return jsonify({'materialEscolar': material}), 200
    except Exception as e:
        print(f"Error al obtener material escolar por id: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al obtener material escolar'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@material_escolar.route('/materiales-escolares/<int:material_id>', methods=['DELETE'])
def delete_material_escolar(material_id):
    conn = None
    cursor = None
    try:
        if not material_id:
            return jsonify({'error': 'ID del material escolar es requerido'}), 400

        conn = db.connect()
        cursor = conn.cursor()
        # Obtenemos la ruta del video y de la imagen para eliminarlos del servidor
        query_select = "SELECT imagen, video FROM material_escolar WHERE id = %s"
        cursor.execute(query_select, (material_id,))
        material = cursor.fetchone()
        if not material:
            return jsonify({'error': 'Material escolar no encontrado'}), 404
        if isinstance(material, dict):
            imagen_path = material.get('imagen')
            video_path = material.get('video')
        elif isinstance(material, (tuple, list)) and len(material) >= 2:
            imagen_path, video_path = material['imagen'], material['video']
        else:
            imagen_path, video_path = None, None

        if imagen_path:
            try:
                os.remove(os.path.join(SERVER_ROOT, imagen_path))
            except Exception as e:
                print(f"Error al eliminar imagen del material escolar: {type(e).__name__}: {e!r}")
        if video_path:
            try:
                os.remove(os.path.join(SERVER_ROOT, video_path))
            except Exception as e:
                print(f"Error al eliminar video del material escolar: {type(e).__name__}: {e!r}")
        

        query = "DELETE FROM material_escolar WHERE id = %s"
        cursor.execute(query, (material_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Material escolar no encontrado'}), 404

        return jsonify({'message': 'Material escolar eliminado exitosamente'}), 200
    except Exception as e:
        print(f"Error al eliminar material escolar: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al eliminar material escolar'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@material_escolar.route('/materiales-escolares/<int:material_id>', methods=['PUT'])
def update_material_escolar(material_id):
    conn = None
    cursor = None
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        color = data.get('color')
        pictograma_id = data.get('pictogramaId')
        cantidad = data.get('cantidad')
        forma = data.get('forma')
        tamaño = data.get('tamaño')
        imagen = data.get('imagen')
        video = data.get('video')  
        imagen_modificada = bool(data.get('imagenModificada'))
        video_modificada = bool(data.get('videoModificada'))


        if not material_id:
            return jsonify({'error': 'ID del material escolar es requerido'}), 400

        conn = db.connect()
        cursor = conn.cursor()

        # Verificamos si el material escolar existe
        query_select = "SELECT imagen, video FROM material_escolar WHERE id = %s"
        cursor.execute(query_select, (material_id,))
        material = cursor.fetchone()
        if not material:
            return jsonify({'error': 'Material escolar no encontrado'}), 404
        if isinstance(material, dict):
            imagen_path_db = material.get('imagen')
            video_path_db = material.get('video')
        elif isinstance(material, (tuple, list)) and len(material) >= 2:
            imagen_path_db, video_path_db = material['imagen'], material['video']
        else:
            imagen_path_db, video_path_db = None, None

        if imagen_modificada:
            imagen_path_new = _save_base64_file(imagen, 'imagenes', 'jpg') if imagen else imagen_path_db
        else:
            imagen_path_new = imagen_path_db

        if video_modificada:
            video_path_new  = _save_base64_file(video, 'videos', 'mp4') if video else video_path_db
        else:
            video_path_new = video_path_db

        
        query_update = """
            UPDATE material_escolar
            SET nombre=%s, color=%s, pictogramaId=%s, cantidad=%s, forma=%s, tamaño=%s, imagen=%s, video=%s
            WHERE id=%s
        """
        cursor.execute(query_update, (nombre, color, pictograma_id, cantidad, forma, tamaño, imagen_path_new, video_path_new, material_id))
        conn.commit()

        if cursor.rowcount == 0:
            # En MySQL, rowcount puede ser 0 cuando el registro existe pero no hubo cambios.
            return jsonify({'message': 'No se detectaron cambios en el material escolar'}), 200

        
        if imagen and imagen_path_db and imagen_path_db != imagen_path_new:
            try:
                os.remove(os.path.join(SERVER_ROOT, imagen_path_db))
            except Exception as e:
                print(f"Error al eliminar imagen antigua del material escolar: {type(e).__name__}: {e!r}")
        if video and video_path_db and video_path_db != video_path_new:
            try:
                os.remove(os.path.join(SERVER_ROOT, video_path_db))
            except Exception as e:
                print(f"Error al eliminar video antiguo del material escolar: {type(e).__name__}: {e!r}")
    
        return jsonify({'message': 'Material escolar actualizado exitosamente'}), 200
    except Exception as e:
        print(f"Error al actualizar material escolar: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al actualizar material escolar'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@material_escolar.route('/materiales-escolares/inventario/pdf', methods=['GET'])
def descargar_inventario_material_escolar_pdf():
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        query = """
            SELECT nombre, color, cantidad, forma, tamaño
            FROM material_escolar
            ORDER BY nombre ASC
        """
        cursor.execute(query)
        materiales = cursor.fetchall()

        if not materiales:
            return jsonify({'error': 'No hay materiales escolares en inventario'}), 404

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf = canvas.Canvas(tmp.name, pagesize=A4)
        width, height = A4
        margin_x = 40
        y = height - 45

        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawString(margin_x, y, 'Inventario de material escolar')
        y -= 24
        pdf.setFont('Helvetica', 10)
        pdf.setFillColor(colors.grey)
        pdf.drawString(margin_x, y, f'Total de items: {len(materiales)}')
        pdf.setFillColor(colors.black)
        y -= 22

        table_x = margin_x
        table_width = width - (2 * margin_x)
        header_h = 20
        row_h = 18
        col_widths = [35, 170, 90, 60, 90, 80]  # N, Nombre, Color, Cantidad, Forma, Tamano
        headers = ['N', 'Nombre', 'Color', 'Cant.', 'Forma', 'Tamano']

        def draw_table_header(current_y):
            pdf.setFillColor(colors.HexColor('#1F4E79'))
            pdf.rect(table_x, current_y - header_h, table_width, header_h, fill=1, stroke=0)
            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 10)
            x = table_x + 4
            for i, title in enumerate(headers):
                pdf.drawString(x, current_y - 14, title)
                x += col_widths[i]
            pdf.setFillColor(colors.black)
            pdf.setStrokeColor(colors.HexColor('#B0B0B0'))
            pdf.setLineWidth(0.6)
            pdf.rect(table_x, current_y - header_h, table_width, header_h, fill=0, stroke=1)
            return current_y - header_h

        y = draw_table_header(y)

        for idx, material in enumerate(materiales, start=1):
            if y - row_h < 45:
                pdf.showPage()
                y = height - 45
                pdf.setFont('Helvetica-Bold', 16)
                pdf.drawString(margin_x, y, 'Inventario de material escolar')
                y -= 24
                pdf.setFont('Helvetica', 10)
                pdf.setFillColor(colors.grey)
                pdf.drawString(margin_x, y, f'Total de items: {len(materiales)}')
                pdf.setFillColor(colors.black)
                y -= 22
                y = draw_table_header(y)

            nombre = material.get('nombre', '') if isinstance(material, dict) else ''
            color_hex = material.get('color', '') if isinstance(material, dict) else ''
            color = _color_name_from_hex(color_hex)
            cantidad = material.get('cantidad', '') if isinstance(material, dict) else ''
            forma = material.get('forma', '') if isinstance(material, dict) else ''
            tamano = material.get('tamaño', '') if isinstance(material, dict) else ''

            if idx % 2 == 0:
                pdf.setFillColor(colors.HexColor('#F5F7FA'))
                pdf.rect(table_x, y - row_h, table_width, row_h, fill=1, stroke=0)
            pdf.setFillColor(colors.black)

            values = [
                str(idx),
                str(nombre)[:32],
                str(color)[:15],
                str(cantidad),
                str(forma)[:16],
                str(tamano)[:14],
            ]

            try:
                cantidad_num = int(cantidad)
            except (TypeError, ValueError):
                cantidad_num = None

            cell_x = table_x
            for i, val in enumerate(values):
                if cantidad_num == 0:
                    pdf.setFillColor(colors.HexColor('#D32F2F'))
                    pdf.rect(cell_x, y - row_h, col_widths[i], row_h, fill=1, stroke=0)
                    pdf.setFillColor(colors.white)
                    pdf.setFont('Helvetica-Bold', 9)
                else:
                    pdf.setFillColor(colors.black)
                    pdf.setFont('Helvetica', 9)

                pdf.drawString(cell_x + 4, y - 13, val)
                cell_x += col_widths[i]

            pdf.setFillColor(colors.black)

            pdf.setStrokeColor(colors.HexColor('#D0D0D0'))
            pdf.setLineWidth(0.4)
            pdf.rect(table_x, y - row_h, table_width, row_h, fill=0, stroke=1)

            y -= row_h

        pdf.save()

        return send_file(
            tmp.name,
            as_attachment=True,
            download_name='inventario_material_escolar.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error al generar PDF de inventario: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al generar inventario en PDF'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@material_escolar.route('/material-seleccionado', methods=['POST'])
def material_seleccionado():
    conn = None
    cursor = None
    try: 
        conn = db.connect()
        cursor = conn.cursor()
        data = request.get_json()
        profesor_id = data.get('profesor_id')
        material_id = data.get('material_id')
        fecha = data.get('fecha')
        if not all([profesor_id, material_id, fecha]):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        query = """UPDATE profesor_material_pedido SET seleccionado = TRUE
                   WHERE profesor_id = %s AND material_id = %s AND fecha_asignacion = %s"""
        cursor.execute(query, (profesor_id, material_id, fecha))
        conn.commit()
        return jsonify({'seleccionado': True}), 200
    except Exception as e:
        print(f"Error al marcar material como seleccionado: {type(e).__name__}: {e!r}")
        print(traceback.format_exc())
        return jsonify({'error': 'Error al marcar material como seleccionado'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()