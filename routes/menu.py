from flask import Blueprint, request
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from db import Database
from const import LIMIT

import os

db = Database()
UPLOAD_FOLDER = os.getenv('FILE_PATH')

menu = Blueprint("menu", __name__)

@menu.route('/menu')
def get_menus():
    conn = None
    cursor = None
    LIMIT_DEFAULT = 10

    try: 
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', LIMIT_DEFAULT))
        fecha = request.args.get('fecha', None)
        
        if offset < 0: offset = 0
        if limit <= 0: limit = LIMIT_DEFAULT
    except ValueError: 
        offset = 0
        limit = LIMIT_DEFAULT

    try: 
        conn = db.connect()
        cursor = conn.cursor() 

       
        query_menus = """
            SELECT id, fecha, id_pictograma, tachado, descripcion 
            FROM menu_diario 
            WHERE (%s IS NULL OR fecha = %s)
            ORDER BY fecha DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query_menus, (fecha, fecha, limit, offset))
        menus_db = cursor.fetchall()

        
        if not menus_db:
            return {'message': 'No se encontraron menús para la fecha seleccionada'}, 404
        
        query_count = "SELECT COUNT(*) as total FROM menu_diario WHERE (%s IS NULL OR fecha = %s)"
        cursor.execute(query_count, (fecha, fecha))
        total_count = cursor.fetchone()['total']

        menu_list = []

        
        for m in menus_db:
            query_platos = """
                SELECT p.nombre, p.id_pictograma, mp.categoria
                FROM menu_platos mp
                JOIN platos p ON mp.id_plato = p.id
                WHERE mp.id_menu = %s
            """
            cursor.execute(query_platos, (m['id'],))
            platos = cursor.fetchall()

            menu_list.append({
                'id': m['id'],
                'fecha': str(m['fecha']), 
                'id_pictograma': m['id_pictograma'],
                'tachado': m['tachado'],
                'descripcion': m['descripcion'],
                'platos': platos 
            })

        return {
            'menus': menu_list, 
            'offset': offset + limit, 
            'count': total_count,
        }, 200

    except Exception as e: 
        print(f"Error en servidor: {e}")
        return {'error': str(e)}, 500
    finally: 
        if cursor: cursor.close()
        if conn: conn.close()

@menu.route('/menu', methods=['POST'])
def create_menu():
    conn = None
    cursor = None
    try: 
        data = request.get_json()
        
        fecha = data.get('fecha')
        id_pictograma_diario = data.get('pictogramaMenuId')
        tachado_diario = data.get('tachado', 0) 
        descripcion = data.get('descripcion', '')

        
        platos_data = [
            {'nombre': data.get('primerPlato'), 'id_picto': data.get('primerPlatoId'), 'cat': 'primero'},
            {'nombre': data.get('segundoPlato'), 'id_picto': data.get('segundoPlatoId'), 'cat': 'segundo'},
            {'nombre': data.get('guarnicion'), 'id_picto': data.get('guarnicionId'), 'cat': 'guarnicion'},
            {'nombre': data.get('postre'), 'id_picto': data.get('postreId'), 'cat': 'postre'}
        ]

        conn = db.connect()
        cursor = conn.cursor()

        query_menu = "INSERT INTO menu_diario (fecha, id_pictograma, tachado, descripcion) VALUES (%s, %s, %s, %s)"
        cursor.execute(query_menu, (fecha, id_pictograma_diario, tachado_diario, descripcion))
        menu_id = cursor.lastrowid 

        
        for plato in platos_data:
            if plato['nombre'] and plato['id_picto']: 
                
                query_plato = "INSERT INTO platos (nombre, id_pictograma) VALUES (%s, %s)"
                cursor.execute(query_plato, (plato['nombre'], plato['id_picto']))
                plato_id = cursor.lastrowid

                query_relacion = "INSERT INTO menu_platos (id_menu, id_plato, categoria) VALUES (%s, %s, %s)"
                cursor.execute(query_relacion, (menu_id, plato_id, plato['cat']))

        conn.commit()
        return {'message': 'Menú completo creado con éxito', 'id_menu': menu_id}, 201

    except Exception as e:
        if conn: conn.rollback() 
        return {'error': str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@menu.route('/menu/<int:menu_id>')
def get_menu_details(menu_id):
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        
        query_menu = "SELECT id, fecha, id_pictograma, tachado, descripcion FROM menu_diario WHERE id = %s"
        cursor.execute(query_menu, (menu_id,))
        menu = cursor.fetchone()

        if not menu:
            return {'message': 'Menú no encontrado'}, 404

        
        query_platos = """
            SELECT p.nombre, p.id_pictograma, mp.categoria
            FROM menu_platos mp
            JOIN platos p ON mp.id_plato = p.id
            WHERE mp.id_menu = %s
        """
        cursor.execute(query_platos, (menu_id,))
        platos = cursor.fetchall()

        menu_details = {
            'id': menu['id'],
            'fecha': str(menu['fecha']),
            'id_pictograma': menu['id_pictograma'],
            'tachado': menu['tachado'],
            'descripcion': menu['descripcion'],
            'platos': platos
        }

        return {'menu': menu_details}, 200

    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()