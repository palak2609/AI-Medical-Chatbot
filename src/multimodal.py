import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

load_dotenv()

from src.voice_input import transcribe_audio
from src.voice_output import text_to_speech
from src.rag_pipeline import ask_rag
from src.vision import analyze_image_with_query
from src.emergency import detect_emergency
from src.hospital_finder import find_nearby_hospitals
from src.severity import detect_severity
from src.context_engine import build_context


def process(
    audio_path=None,
    text_input=None,
    image_path=None,
    conversation_history=None,
):
    if conversation_history is None:
        conversation_history = []

    # 1. Resolve query text
    if audio_path:
        query = transcribe_audio(audio_path)
    else:
        query = (text_input or "").strip()

    if not query and not image_path:
        return {
            "query": "",
            "response": "Please describe your symptoms via text, voice, or upload a medical image.",
            "severity": "MILD",
            "is_emergency": False,
            "hospitals": None,
            "audio_bytes": None,
        }

    # 2. Build history context
    history_text = ""
    for msg in conversation_history[-6:]:
        role = "Patient" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    full_query = (history_text + f"Patient: {query}").strip() if history_text else query

    # 3. Environmental context
    env_context = build_context()

    # 4. Triage — run both LLM calls in parallel to halve wait time
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_severity = executor.submit(detect_severity, full_query)
        f_emergency = executor.submit(detect_emergency, full_query)
        severity = f_severity.result()
        is_emergency = f_emergency.result()

    # 5. Generate response
    hospitals = None

    if is_emergency:
        severity = "EMERGENCY"
        hospitals = find_nearby_hospitals()
        response = (
            "## 🚨 EMERGENCY ALERT\n\n"
            "Your symptoms may indicate a **life-threatening medical emergency**.\n\n"
            "### Immediate Actions:\n"
            "- **Call emergency services immediately: 112 (India) / 911 (US)**\n"
            "- Do not drive yourself to the hospital\n"
            "- Stay calm and keep someone with you\n\n"
            "---\n\n"
            f"### Nearby Hospitals:\n{hospitals}\n\n"
            "---\n"
            "*This AI cannot replace emergency medical care. Please seek help immediately.*"
        )

    elif image_path:
        image_query = (
            f"{env_context}\n\n"
            f"Conversation so far:\n{history_text}\n"
            f"Patient query: {query or 'Please analyze this medical image.'}"
        ).strip()
        response = analyze_image_with_query(image_path, image_query)

    else:
        rag_query = (
            f"{env_context}\n\n"
            f"Conversation so far:\n{history_text}\n"
            f"Patient query: {query}"
        ).strip()
        response = ask_rag(rag_query)

    # 6. Voice output
    try:
        audio_out = text_to_speech(response)
    except Exception:
        audio_out = None

    return {
        "query": query,
        "response": response,
        "severity": severity,
        "is_emergency": is_emergency,
        "hospitals": hospitals,
        "audio_bytes": audio_out,
    }
