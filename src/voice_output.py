import re
import tempfile
import os
from gtts import gTTS


def _strip_md(text: str) -> str:
    """Remove markdown syntax so gTTS reads clean prose."""
    text = re.sub(r'#{1,6}\s*', '', text)                          # headings
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)        # bold / italic
    text = re.sub(r'`[^`]*`', '', text)                            # inline code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)          # links
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)      # bullets
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)      # numbered lists
    text = re.sub(r'-{3,}', '.', text)                             # horizontal rules → pause
    text = re.sub(r'\|[^\n]*', '', text)                           # table rows
    text = re.sub(r'[✅🔴🟡⚠️🚨📋🔍🩺❓]', '', text)             # medical emojis
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def text_to_speech(text: str) -> bytes:
    clean = _strip_md(text)
    # Keep under 2000 chars so gTTS doesn't time out
    tts_text = clean[:2000] if len(clean) > 2000 else clean
    if not tts_text:
        return b""

    tts = gTTS(tts_text)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()
    try:
        tts.save(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)
