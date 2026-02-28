import os
from openai import OpenAI
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path

openAi = Blueprint('openAI', __name__)

client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

@openAi.route("/speech-to-text", methods=['POST'])
def speech_to_text():
    if 'audio' not in request.files:
        return {"error": "No audio"}, 400

    audio = request.files['audio']

    with open("temp.m4a", "wb") as f:
        f.write(audio.read())

    transcription = client.audio.transcriptions.create(
        file=open("temp.m4a", "rb"),
        model="whisper-1",
        language="es"
    )

    return {"text": transcription.text}

@openAi.route('/generar-voz', methods=['GET'])
def generar_voz(): 
    texto = request.args.get('texto', '')
    
    if not texto:
        return {"error": "No se proporcionó texto"}, 400

    try:
        # Definimos la ruta temporal para el archivo de audio
        speech_file_path = Path(__file__).parent / "temp_speech.mp3"
        
        # Llamada a OpenAI para generar voz realista
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer",  # Opciones: alloy, echo, fable, onyx, nova, shimmer
            input=texto
        )

        # Guardamos el archivo binario
        response.stream_to_file(speech_file_path)

        # Enviamos el archivo al cliente
        return send_file(
            str(speech_file_path), 
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        print(f"Error generando audio: {e}")
        return {"error": str(e)}, 500
