from flask import Blueprint, request, jsonify
from db import Database
from const import LIMIT
from flask_jwt_extended import jwt_required, get_jwt

import os

db = Database()
UPLOAD_FOLDER = os.getenv('FILE_PATH')

menu = Blueprint("menu", __name__)

@menu.route('/menu')
@jwt_required()
def get_menus():
    conn = None
    cursor = None
    try: 
        claims = get_jwt()
        if claims.get('tipo') != 'admin' and claims.get('tipo') != 'profesor' and claims.get('tipo') != 'estudiante': 
            return {"error": "Acceso no autorizado"}, 403
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', LIMIT))
        categoria = request.args.get('categoria', 'menu')
        
        if offset < 0: offset = 0
        if limit <= 0: limit = LIMIT
    except ValueError: 
        offset = 0
        limit = LIMIT

    try: 
        conn = db.connect()
        cursor = conn.cursor() 

        query_menus = """
            SELECT id, id_pictograma, tachado, descripcion FROM menu WHERE categoria = %s
            ORDER BY descripcion
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query_menus, (categoria, limit, offset))
        menus_db = cursor.fetchall()
        if not menus_db:
            return {'message': 'No se encontraron menús disponibles'}, 404
        
        query_count = "SELECT COUNT(*) as total FROM menu WHERE categoria = %s"
        cursor.execute(query_count, (categoria,))
        total_count = cursor.fetchone()['total']

        menu_list = []

        for menu in menus_db:
            query_platos = """
                SELECT p.nombre, p.id_pictograma, p.id
                FROM menu_plato mp
                JOIN platos p ON mp.plato_id = p.id
                WHERE mp.menu_id = %s
            """
            cursor.execute(query_platos, (menu['id'],))
            platos = cursor.fetchall()

            menu_list.append({
                'id': menu['id'], 
                'id_pictograma': menu['id_pictograma'],
                'tachado': bool(menu['tachado']),
                'descripcion': menu['descripcion'],
                'platos': platos 
            })

        return {
            'menus': menu_list, 
            'offset': offset + limit, 
            'count': total_count,
        }, 200

    except Exception as e: 
        print(str(e))
        return {'error': str(e)}, 500
    finally: 
        if cursor: cursor.close()
        if conn: conn.close()

@menu.route('/menu', methods=['POST'])
@jwt_required()
def create_menu():
    conn = None
    cursor = None
    try: 
        claims = get_jwt()
        if claims.get('tipo') != 'admin': 
            return {"error": "Acceso no autorizado"}, 403
        conn = db.connect()
        cursor = conn.cursor() 
        data = request.get_json()

        if not data.get('menu'):
            return {"message": "El campo menú no puede ser vacio"}, 400
        
        menu_data = data.get('menu')
        if menu_data.get("id_pictograma") is None or menu_data.get("tachado") is None or menu_data.get("descripcion") is None or menu_data.get("categoria") is None: 
            return {"message": "Todos los campos son necesarios"}, 400
        
        id_pictograma = menu_data.get("id_pictograma")
        tachado = bool(menu_data.get("tachado"))
        descripcion = menu_data.get("descripcion")
        categoria = menu_data.get("categoria")
        
        query = f"""INSERT INTO menu (id_pictograma, tachado, descripcion, categoria) VALUES (%s, %s, %s, %s)"""

        cursor.execute(query, (id_pictograma, tachado, descripcion, categoria, ))
        conn.commit()
        
        menu_id = cursor.lastrowid
        
        if menu_id is None: 
            return {"message": "Error al insertar el menú"}, 500

        if menu_data.get("platos") is None: 
            return {"message": "Todos los campos son necesarios"}, 400
        
        platos = menu_data.get("platos")

        for plato in platos: 
            if plato.get("id_pictograma") is None or plato.get("nombre") is None or plato.get("categoria") is None: 
                return {"message": "Todos los campos son necesarios"}, 400
            id_pictograma = plato.get("id_pictograma")
            nombre = plato.get("nombre")
            categoria = plato.get("categoria")
            
            query = f"""INSERT INTO platos (id_pictograma, nombre, categoria) VALUES (%s, %s, %s)"""

            cursor.execute(query, (id_pictograma, nombre, categoria, ))
            conn.commit()
            plato_id = cursor.lastrowid
            if plato_id is None: 
                return {"message": "Error al insertar el plato"}, 500
            
            query = f"""INSERT INTO menu_plato (menu_id, plato_id) VALUES (%s, %s)"""
            cursor.execute(query, (menu_id, plato_id))
            conn.commit()
            menu_plato_id = cursor.lastrowid
            if menu_plato_id is None:
                return {"message": "Error al asociar el plato con el menú"}, 500
            
        return {"message": "Se ha añadido los platos correctamente"}, 200
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(str(e))
        return jsonify({"ok": False, "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()   

@menu.route('/menu/<int:menu_id>', methods=['PUT'])
@jwt_required()
def update_menu(menu_id):
    conn = None
    cursor = None
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'admin': 
            return {"error": "Acceso no autorizado"}, 403

        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "message": "No se han recibido parámetros"}), 400

        conn = db.connect()
        cursor = conn.cursor()

        # Construir dinámicamente los campos del menú a actualizar
        campos = []
        valores = []

        if 'fecha' in data:
            campos.append("fecha = %s")
            valores.append(data['fecha'])
        if 'pictogramaMenuId' in data:
            campos.append("id_pictograma = %s")
            valores.append(data['pictogramaMenuId'])
        if 'tachado' in data:
            campos.append("tachado = %s")
            valores.append(data['tachado'])
        if 'descripcion' in data:
            campos.append("descripcion = %s")
            valores.append(data['descripcion'])

        if campos:
            update_menu_query = f"""
                UPDATE menu_diario
                SET {', '.join(campos)}
                WHERE id = %s
            """
            valores.append(menu_id)
            cursor.execute(update_menu_query, tuple(valores))

        # Actualizar solo los platos que vienen en el JSON
        platos_data = [
            {'nombre': data.get('primerPlato'), 'id_picto': data.get('primerPlatoId'), 'cat': 'primero'},
            {'nombre': data.get('segundoPlato'), 'id_picto': data.get('segundoPlatoId'), 'cat': 'segundo'},
            {'nombre': data.get('guarnicion'), 'id_picto': data.get('guarnicionId'), 'cat': 'guarnicion'},
            {'nombre': data.get('postre'), 'id_picto': data.get('postreId'), 'cat': 'postre'}
        ]

        for plato in platos_data:
            if plato['nombre'] is not None and plato['id_picto'] is not None:
                update_plato_query = """
                    UPDATE platos p
                    JOIN menu_platos mp ON p.id = mp.id_plato
                    SET p.nombre = %s, p.id_pictograma = %s
                    WHERE mp.id_menu = %s AND mp.categoria = %s
                """
                cursor.execute(update_plato_query, (plato['nombre'], plato['id_picto'], menu_id, plato['cat']))

        conn.commit()
        return jsonify({"ok": True, "message": "Menú actualizado correctamente"}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@menu.route('/menu/<int:menu_id>')
@jwt_required()
def get_menu_details(menu_id):
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'profesor' and claims.get('tipo') != 'estudiante': 
        return {"error": "Acceso no autorizado"}, 403

    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        
        query_menu = "SELECT id, id_pictograma, tachado, descripcion, categoria FROM menu WHERE id = %s"
        cursor.execute(query_menu, (menu_id,))
        menu = cursor.fetchone()

        if not menu:
            return {'message': 'Menú no encontrado'}, 404

        
        query_platos = """
            SELECT p.nombre, p.id_pictograma, p.categoria
            FROM menu_plato mp
            JOIN platos p ON mp.plato_id = p.id
            WHERE mp.menu_id = %s
        """
        cursor.execute(query_platos, (menu_id,))
        platos = cursor.fetchall()

        menu_details = {
            'id': menu['id'],
            'id_pictograma': menu['id_pictograma'],
            'tachado': menu['tachado'],
            'descripcion': menu['descripcion'],
            'categoria': menu['categoria'],
            'platos': platos
        }

        return {'menu': menu_details}, 200
   # id, id_pictograma, nombre
    except Exception as e:
        print(str(e))
        return {'error': str(e)}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@menu.route('/menu-dia', methods=['GET'])
@jwt_required()

def get_menu_dia():
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'profesor' and claims.get('tipo') != 'estudiante': 
        return {"error": "Acceso no autorizado"}, 403


    fecha = request.args.get('fecha')
    id_visita = request.args.get('id_visita') 
    
    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor() 
        
        visita_id = id_visita if id_visita else 0

       
        query_platos = """
            SELECT 
                p.id as id_plato, 
                p.nombre, 
                p.id_pictograma, 
                mp.categoria as plato_tipo, 
                md.descripcion as nombre_menu,
                md.id as id_menu,
                IFNULL(pp.cantidad, 0) as cantidad_guardada
            FROM platos p
            JOIN menu_platos mp ON p.id = mp.id_plato
            JOIN menu_diario md ON mp.id_menu = md.id
            LEFT JOIN pedido_platos pp ON pp.id_plato = p.id 
                AND pp.id_menu = md.id 
                AND pp.id_comanda_aula = %s
            WHERE md.fecha = %s AND mp.categoria != 'postre'
        """
        cursor.execute(query_platos, (visita_id, fecha))
        platos = cursor.fetchall()

        
        query_postres = """
            SELECT 
                p.id as id_postre, 
                p.nombre, 
                p.id_pictograma, 
                md.descripcion as nombre_menu,
                md.id as id_menu,
                IFNULL(pp.cantidad, 0) as cantidad_guardada
            FROM platos p
            JOIN menu_platos mp ON p.id = mp.id_plato AND mp.categoria = 'postre'
            JOIN menu_diario md ON mp.id_menu = md.id
            LEFT JOIN pedido_platos pp ON pp.id_plato = p.id 
                AND pp.id_menu = md.id 
                AND pp.id_comanda_aula = %s
            WHERE md.fecha = %s
        """
        cursor.execute(query_postres, (visita_id, fecha))
        postres = cursor.fetchall()
        
        return jsonify({"platos": platos, "postres": postres}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@menu.route('/menu/<int:menu_id>', methods=['DELETE'])
@jwt_required()
def delete_menu(menu_id):
    claims = get_jwt()
    if claims.get('tipo') != 'admin': 
        return {"error": "Acceso no autorizado"}, 403

    conn = None
    cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()

        #obtenemos los platos asociados a ese menú para eliminarlos después
        query = """SELECT plato_id FROM menu_plato WHERE menu_id = %s"""
        cursor.execute(query, (menu_id,))

        platos_asociados = cursor.fetchall()

        if not platos_asociados:
            return {"message": "No se encontró el menú o no tiene platos asociados"}, 404
        # Eliminamos todos los platos asociados al menú 
        for plato in platos_asociados:
            plato_id = plato['plato_id']
            query = """DELETE FROM platos WHERE id = %s"""
            cursor.execute(query, (plato_id,))
            #Compribamos si se ha eliminado el plato correctamente
            if cursor.rowcount == 0:
                conn.rollback()
                return {"message": f"Error al eliminar el plato con id {plato_id}"}, 500
        # Finalmente, eliminar el menú
        query = """DELETE FROM menu WHERE id = %s"""
        cursor.execute(query, (menu_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"message": "No se encontró el menú"}, 404
        return jsonify({"ok": True, "message": "Menú eliminado correctamente"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(str(e))
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@menu.route('/menu/<string:name>')
@jwt_required()
def get_menu(name): 
    claims = get_jwt()
    if claims.get('tipo') != 'admin' and claims.get('tipo') != 'profesor' and claims.get('tipo') != 'estudiante': 
        return {"error": "Acceso no autorizado"}, 403

    conn = None
    cursor = None
    try: 
        categoria = request.args.get('categoria', 'menu')
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
        except (ValueError, TypeError): 
            limit = LIMIT
        
        conn = db.connect()
        cursor = conn.cursor()


        name_pattern = f"%{name}%"

        query = f"""
        SELECT id, id_pictograma, tachado, descripcion
        FROM menu
        WHERE descripcion LIKE %s
        AND categoria = %s
        ORDER BY descripcion
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, (name_pattern, categoria, limit, offset,))
        menus = cursor.fetchall()

        if not menus: 
            return {"message": "No se encontraron menús con ese nombre"}, 404
        query = f"""SELECT COUNT(*) as total FROM menu WHERE descripcion LIKE %s AND categoria = %s"""
        cursor.execute(query, (name_pattern, categoria))
        total_count = cursor.fetchone()['total']
        
        menu_list = []

        for menu in menus: 
            query_platos = """
                SELECT p.nombre, p.id_pictograma
                FROM menu_plato mp
                JOIN platos p ON mp.plato_id = p.id
                WHERE mp.menu_id = %s
            """
            cursor.execute(query_platos, (menu['id'], ))
            platos = cursor.fetchall()

            menu_list.append({
                'id': menu['id'],
                'id_pictograma': menu['id_pictograma'],
                'tachado': menu['tachado'],
                'descripcion': menu['descripcion'],
                'platos': platos
            })

        return {
            'menus': menu_list,
            'offset': offset + limit,
            'count': total_count
        }, 200
    except Exception as e: 
        print(str(e))
        return {'error': str(e)}, 500
    finally: 
        if cursor: cursor.close()
        if conn: conn.close()

    