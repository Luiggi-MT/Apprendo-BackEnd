import pytest
import io
from unittest.mock import MagicMock, patch
from routes import students as students_module

@pytest.fixture
def mock_db(monkeypatch):
    """Fixture para simular la base de datos globalmente en este archivo"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr(students_module.db, "connect", lambda: mock_conn)
    return mock_conn, mock_cursor

def test_get_students_success(client, mock_db):
    """Prueba la obtención de la lista de estudiantes con paginación"""
    conn, cursor = mock_db
    
    # Configuramos el mock para devolver una lista de estudiantes
    cursor.fetchall.return_value = [
        {
            'foto': '1/foto.jpg', 'username': 'alumno1', 'tipoContraseña': 'texto',
            'accesibilidad': 'visual,auditiva', 'preferenciasVisualizacion': '{}',
            'asistenteVoz': 1, 'id': 1, 'sexo': 'M'
        }
    ]
    cursor.fetchone.return_value = (1,) # Para el COUNT(*)

    response = client.get('/students?offset=0&limit=10')

    assert response.status_code == 200
    data = response.get_json()
    assert len(data['students']) == 1
    assert data['students'][0]['username'] == 'alumno1'
    # Verificamos que el split(',') de accesibilidad funcionó
    assert data['students'][0]['accesibilidad'] == ['visual', 'auditiva']

def test_create_student_success(client, mock_db):
    """Prueba la creación de un estudiante (POST)"""
    conn, cursor = mock_db
    cursor.lastrowid = 99 # ID simulado del nuevo estudiante

    payload = {
        "username": "nuevo_alumno",
        "tipoContraseña": "texto",
        "contraseña": "password123",
        "preferenciasVisualizacion": "modo-oscuro",
        "asistenteVoz": 0,
        "sexo": "F",
        "accesibilidad": ["visual"]
    }

    response = client.post('/student', json=payload)

    assert response.status_code == 201
    assert response.get_json()['id'] == 99
    conn.commit.assert_called_once()

def test_delete_student_success(client, mock_db, monkeypatch):
    """Prueba el borrado de un estudiante y su carpeta física"""
    conn, cursor = mock_db
    
    # 1. Simular que el estudiante existe
    cursor.fetchone.return_value = {'id': 10}
    cursor.rowcount = 1
    
    # 2. Mockear shutil.rmtree y os.path.exists para no borrar carpetas reales
    mock_rmtree = MagicMock()
    monkeypatch.setattr("shutil.rmtree", mock_rmtree)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr(students_module, "UPLOAD_FOLDER", "/tmp/fake_path")

    response = client.delete('/student/alumno_a_borrar')

    assert response.status_code == 200
    assert response.get_json()['message'] == "Deleted Student successful"
    mock_rmtree.assert_called_once()
    conn.commit.assert_called_once()

@patch("glob.glob")
def test_upload_student_photo(mock_glob, client, mock_db, monkeypatch, tmp_path):
    """Prueba la subida de foto de perfil (Multipart POST)"""
    conn, cursor = mock_db
    mock_glob.return_value = [] # No hay fotos anteriores
    
    # Configurar carpetas temporales
    fake_upload = tmp_path / "uploads"
    fake_upload.mkdir()
    monkeypatch.setattr(students_module, "UPLOAD_FOLDER", str(fake_upload))
    
    data = {
        'photo': (io.BytesIO(b"fake_image_content"), 'perfil.png')
    }

    response = client.post('/student/1/photo', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    # Verificar que el archivo se guardó físicamente en la carpeta del ID
    assert (fake_upload / "1" / "fotoPerfil.png").exists()

def test_get_student_by_name(client, mock_db):
    conn, cursor = mock_db
    # Simulamos que encuentra un estudiante que coincide con el nombre
    cursor.fetchall.return_value = [{
        'foto': '2/perfil.png', 'username': 'luiggi', 'tipoContraseña': 'imagenes',
        'accesibilidad': 'auditiva', 'preferenciasVisualizacion': '{}',
        'asistenteVoz': 1, 'sexo': 'M'
    }]
    cursor.fetchone.return_value = (1,) # Resultado del COUNT(*)

    response = client.get('/students/luiggi?limit=5')

    assert response.status_code == 200
    data = response.get_json()
    assert data['students'][0]['username'] == 'luiggi'
    # Verificamos que se construyó el patrón de búsqueda correctamente
    cursor.execute.assert_any_call(
        "SELECT foto, username, tipoContraseña, accesibilidad, preferenciasVisualizacion, asistenteVoz, sexo FROM estudiantes WHERE username LIKE %s ORDER BY username LIMIT %s OFFSET %s",
        ('%luiggi%', 5, 0)
    )

def test_update_student_success(client, mock_db):
    conn, cursor = mock_db
    
    payload = {
        "username": "nombre_editado",
        "accesibilidad": ["visual", "motriz"]
    }

    response = client.put('/student/1', json=payload)

    assert response.status_code == 200
    assert response.get_json()['message'] == "Student updated successfully"
    conn.commit.assert_called_once()
    # Verificamos que se unieron los campos de accesibilidad con comas
    args, _ = cursor.execute.call_args
    assert "username = %s, accesibilidad = %s" in args[0]
    assert "visual,motriz" in args[1]

def test_update_student_success(client, mock_db):
    conn, cursor = mock_db
    
    payload = {
        "username": "nombre_editado",
        "accesibilidad": ["visual", "motriz"]
    }

    response = client.put('/student/1', json=payload)

    assert response.status_code == 200
    assert response.get_json()['message'] == "Student updated successfully"
    conn.commit.assert_called_once()
    # Verificamos que se unieron los campos de accesibilidad con comas
    args, _ = cursor.execute.call_args
    assert "username = %s, accesibilidad = %s" in args[0]
    assert "visual,motriz" in args[1]