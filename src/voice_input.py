import os
from groq import Groq

def transcribe_audio(audio_file):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(audio_file, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3"
        )

    return transcription.text