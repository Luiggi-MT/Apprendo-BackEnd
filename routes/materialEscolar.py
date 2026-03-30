from flask import Blueprint, request, jsonify
from db import Database
import os
import base64
import uuid
import traceback
from const import LIMIT

db = Database()
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MATERIAL_ESCOLAR_FOLDER = os.getenv(
    'MATERIAL_ESCOLAR_PATH',
    os.path.join(SERVER_ROOT, 'media', 'materialEscolar')
)

material_escolar = Blueprint('material_escolar', __name__)


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