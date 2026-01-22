import pytest
import os
from routes import files as files_module

def test_get_foto_success(client, tmp_path, monkeypatch):
    """Prueba éxito en /foto/<filename> usando FOLDER_PATH"""
    # 1. Preparar archivo temporal
    fake_folder = (tmp_path / "uploads").resolve()
    fake_folder.mkdir()
    fake_file = fake_folder / "perfil.jpg"
    fake_file.write_bytes(b"data_foto")

    # 2. Inyectar la variable de entorno en el módulo
    monkeypatch.setattr(files_module, "UPLOAD_FOLDER", str(fake_folder))
    
    # 3. Petición
    response = client.get('/foto/perfil.jpg')
    
    assert response.status_code == 200
    assert response.data == b"data_foto"

def test_get_foto_not_found(client, tmp_path, monkeypatch):
    """Prueba 404 en /foto/<filename>"""
    monkeypatch.setattr(files_module, "UPLOAD_FOLDER", str(tmp_path))
    
    response = client.get('/foto/no_existe.jpg')
    assert response.status_code == 404

def test_get_foto_password_success(client, tmp_path, monkeypatch):
    """Prueba éxito en /foto-password/<filename> usando getcwd()"""
    # 1. Creamos un archivo en una ruta que simularemos como 'current working directory'
    fake_cwd = (tmp_path / "app_root").resolve()
    fake_cwd.mkdir()
    fake_file = fake_cwd / "secret_pass.png"
    fake_file.write_bytes(b"data_password")

    # 2. Mockeamos os.getcwd() para que devuelva nuestra carpeta temporal
    monkeypatch.setattr(os, "getcwd", lambda: str(fake_cwd))
    
    # 3. La ruta usa filename como parte del path relativo al cwd
    response = client.get('/foto-password/secret_pass.png')
    
    assert response.status_code == 200
    assert response.data == b"data_password"

def test_get_foto_password_server_error(client, monkeypatch):
    """Prueba que el Exception general de foto-password funcione (Error 500)"""
    # Saboteamos os.path.join para que explote
    monkeypatch.setattr(os.path, "join", lambda *args: exec('raise(Exception("System Crash"))'))
    
    response = client.get('/foto-password/cualquier_cosa.png')
    
    assert response.status_code == 500
    assert "System Crash" in response.get_json()['error']