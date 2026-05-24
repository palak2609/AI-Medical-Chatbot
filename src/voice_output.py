import tempfile
import os
from gtts import gTTS


def text_to_speech(text: str) -> bytes:
    """Convert text to speech and return audio bytes."""
    # Truncate very long responses so gTTS doesn't time out
    tts_text = text[:3000] if len(text) > 3000 else text

    tts = gTTS(tts_text)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()

    try:
        tts.save(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)
