import pytest
import io
from unittest.mock import MagicMock, patch
from routes import openAi as openai_module

def test_speech_to_text_success(client, monkeypatch):
    """Prueba el flujo exitoso de transcripción"""
    
    # 1. Mock de la respuesta de OpenAI
    mock_transcription = MagicMock()
    mock_transcription.text = "Hola, esta es una prueba de voz."
    
    # Creamos un mock para el cliente de OpenAI
    mock_openai_client = MagicMock()
    mock_openai_client.audio.transcriptions.create.return_value = mock_transcription
    
    # 2. Inyectamos el mock en el módulo de la ruta
    monkeypatch.setattr(openai_module, "client", mock_openai_client)

    # 3. Preparamos un archivo de audio falso en memoria
    data = {
        'audio': (io.BytesIO(b"fake audio data"), 'test.m4a')
    }

    # 4. Ejecución del test
    response = client.post('/speech-to-text', data=data, content_type='multipart/form-data')

    # 5. Aserciones
    assert response.status_code == 200
    assert response.get_json()['text'] == "Hola, esta es una prueba de voz."
    
    # Verificamos que se llamó a OpenAI con los parámetros correctos
    mock_openai_client.audio.transcriptions.create.assert_called_once()
    args, kwargs = mock_openai_client.audio.transcriptions.create.call_args
    assert kwargs['model'] == "whisper-1"
    assert kwargs['language'] == "es"

def test_speech_to_text_no_audio(client):
    """Prueba el error 400 cuando no se envía el archivo"""
    response = client.post('/speech-to-text', data={})
    
    assert response.status_code == 400
    assert response.get_json()['error'] == "No audio"