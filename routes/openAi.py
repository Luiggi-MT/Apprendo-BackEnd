import os
from openai import OpenAI
from flask import Blueprint, request, jsonify

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
