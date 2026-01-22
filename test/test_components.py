import pytest
import os
from routes import components as components_module 

def test_get_component_success(client, tmp_path, monkeypatch):
    """Prueba que se pueda descargar un archivo existente usando el fixture client"""
    # 1. Crear carpeta y archivo temporal
    fake_folder = tmp_path / "components_dir"
    fake_folder.mkdir()
    fake_file = fake_folder / "test_image.png"
    fake_file.write_bytes(b"datos_de_imagen_simulados")

    # 2. Inyectar la ruta temporal directamente en el atributo del módulo cargado
    monkeypatch.setattr(components_module, "FOLDER_COMPONENTS", str(fake_folder))
    
    # 3. Llamada al cliente (Asegúrate de que la ruta coincide con app.py)
    response = client.get('/component/test_image.png')

    # 4. Aserciones
    assert response.status_code == 200
    assert response.data == b"datos_de_imagen_simulados"

def test_get_component_not_found(client, tmp_path, monkeypatch): 
    """Prueba que devuelve 404 si el archivo no existe en el path configurado"""
    monkeypatch.setenv("FILE_COMPONENTS", str(tmp_path))

    response = client.get('/components/not_found.png')
    assert response.status_code == 404

def test_get_component_server_error(client, monkeypatch):
    """Prueba que el bloque 'except Exception' capture errores inesperados"""
    
    # 1. Definimos el error simulado
    def mock_join(*args, **kwargs):
        raise Exception("Error simulado de sistema")
    
    # 2. Corregimos la ruta del atributo: es "os.path.join"
    monkeypatch.setattr(os.path, "join", mock_join)
    
    # 3. Realizamos la petición
    response = client.get('/component/cualquier_cosa.png')
    
    # 4. Verificaciones
    assert response.status_code == 500
    assert response.get_json()['error'] == "Error simulado de sistema"