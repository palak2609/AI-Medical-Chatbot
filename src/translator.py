"""
Multilingual support via deep-translator (Google Translate, free, no API key).
Translation happens client-side: input → English for processing,
English response → user's language for display.
"""

LANGUAGES = {
    "English":    "en",
    "Hindi":      "hi",
    "Tamil":      "ta",
    "Telugu":     "te",
    "Bengali":    "bn",
    "Marathi":    "mr",
    "Gujarati":   "gu",
    "Kannada":    "kn",
    "Spanish":    "es",
    "French":     "fr",
    "Arabic":     "ar",
    "German":     "de",
}


def to_english(text: str, source_code: str) -> str:
    """Translate text from source_code → English. Returns original on failure."""
    if source_code == "en" or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source=source_code, target="en").translate(text)
    except Exception:
        return text


def from_english(text: str, target_code: str) -> str:
    """Translate English text → target_code. Returns original on failure."""
    if target_code == "en" or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        # GoogleTranslator has a 5000-char limit; chunk if needed
        if len(text) <= 4800:
            return GoogleTranslator(source="en", target=target_code).translate(text)
        chunks, result = _chunk(text, 4800), []
        for chunk in chunks:
            result.append(GoogleTranslator(source="en", target=target_code).translate(chunk))
        return " ".join(result)
    except Exception:
        return text


def _chunk(text: str, size: int) -> list:
    """Split text into chunks of at most `size` characters at sentence boundaries."""
    sentences = text.replace("\n", " \n ").split(". ")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < size:
            current += s + ". "
        else:
            if current:
                chunks.append(current.strip())
            current = s + ". "
    if current:
        chunks.append(current.strip())
    return chunks or [text]
