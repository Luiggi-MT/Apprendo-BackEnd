from flask import Blueprint, request
from werkzeug.security import generate_password_hash
from db import Database


admin_test = Blueprint('add_admin_test', __name__)
db = Database()


@admin_test.route('/add_admin_test', methods=['POST'])
def add_admin_test():
    
    if not request.is_json:
        return {'error': 'Missing JSON in request'}, 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {'error': 'Missing username or password'}, 400

    try:
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        conn = db.connect()
        cursor = conn.cursor()
        
        check_query = "SELECT username FROM profesores WHERE username = %s"
        cursor.execute(check_query, (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {'error': f'Admin "{username}" already exists'}, 409

        insert_query = "INSERT INTO  profesores (username, password) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, hashed_password))
        
        conn.commit()
        cursor.close()
        conn.close()

        return {'message': 'Test Admin registered successfully with hashed password'}, 201

    except Exception as e:
        return {'error': str(e)}, 500

