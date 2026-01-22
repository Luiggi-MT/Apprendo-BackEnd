import pytest
from unittest.mock import MagicMock
from werkzeug.security import generate_password_hash
from routes import session as auth_module # Asegúrate de que el nombre del archivo coincida

def test_login_profesor_success(client, monkeypatch):
    """Prueba login exitoso de un profesor"""
    # 1. Mock de la base de datos
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # Simulamos lo que devuelve la base de datos
    hashed_pw = generate_password_hash("password123", method='pbkdf2:sha256')
    mock_cursor.fetchone.return_value = {
        'password': hashed_pw,
        'foto': 'profe.jpg',
        'tipo': 'admin'
    }
    mock_conn.cursor.return_value = mock_cursor
    
    # 2. Inyectamos el mock en la instancia db del módulo
    monkeypatch.setattr(auth_module.db, "connect", lambda: mock_conn)

    # 3. Petición POST
    payload = {"username": "luiggi", "password": "password123"}
    response = client.post('/login', json=payload)

    # 4. Aserciones
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == "luiggi"
    assert data['foto'] == "profe.jpg"
    
    # Verificar que la sesión se guardó (Flask client mantiene las cookies)
    with client.session_transaction() as sess:
        assert sess['logged_in'] is True
        assert sess['username'] == "luiggi"

def test_login_profesor_invalid_password(client, monkeypatch):
    """Prueba error 401 por contraseña incorrecta"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'password': generate_password_hash("real_pass", method='pbkdf2:sha256'), 'foto': 'x.jpg', 'tipo': 'profe'}
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr(auth_module.db, "connect", lambda: mock_conn)

    response = client.post('/login', json={"username": "user", "password": "wrong_password"})

    assert response.status_code == 401
    assert response.get_json()['error'] == "Credenciales invalidas"

def test_get_session_active(client):
    """Prueba que la ruta /session devuelva los datos si hay login previo"""
    # Forzamos datos en la sesión antes de llamar a la ruta
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'test_user'
        sess['foto'] = 'test.png'

    response = client.get('/session')
    
    assert response.status_code == 200
    assert response.get_json()['ok'] is True
    assert response.get_json()['username'] == 'test_user'

def test_logout(client):
    """Prueba que el logout limpie la sesión"""
    with client.session_transaction() as sess:
        sess['logged_in'] = True

    response = client.post('/logout')
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        assert 'logged_in' not in sess