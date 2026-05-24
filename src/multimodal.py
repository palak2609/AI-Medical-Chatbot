import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

load_dotenv()

from src.voice_input    import transcribe_audio
from src.rag_pipeline   import ask_rag
from src.vision         import analyze_image_with_query
from src.emergency      import detect_emergency
from src.hospital_finder import find_nearby_hospitals
from src.severity       import detect_severity
from src.context_engine import build_context

# Common emergency numbers by country (fallback: international)
_EMERGENCY_NUMBERS = {
    "India": "112", "United States": "911", "Canada": "911",
    "United Kingdom": "999", "Australia": "000", "Germany": "112",
    "France": "112", "Spain": "112", "Italy": "112",
    "Pakistan": "115", "Bangladesh": "999", "Sri Lanka": "110",
    "Nepal": "102", "China": "120", "Japan": "119", "Brazil": "192",
}


def _emergency_number(country: str = "") -> str:
    return _EMERGENCY_NUMBERS.get(country, "112 / 911 / 999")


def process(
    audio_path=None,
    text_input=None,
    image_path=None,
    conversation_history=None,
    country: str = "",
):
    if conversation_history is None:
        conversation_history = []

    # 1. Resolve query text
    query = transcribe_audio(audio_path) if audio_path else (text_input or "").strip()

    if not query and not image_path:
        return {
            "query": "",
            "response": "Please describe your symptoms via text, voice, or upload a medical image.",
            "severity": "MILD",
            "is_emergency": False,
            "hospitals": None,
        }

    # 2. Build conversation history context
    history_text = ""
    for msg in conversation_history[-6:]:
        role = "Patient" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    full_query = (history_text + f"Patient: {query}").strip() if history_text else query

    # 3. Environmental context
    env_context = build_context()

    # 4. Parallel triage
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_severity  = executor.submit(detect_severity,  full_query)
        f_emergency = executor.submit(detect_emergency, full_query)
        severity    = f_severity.result()
        is_emergency = f_emergency.result()

    # 5. Generate response
    hospitals = None
    num = _emergency_number(country)

    if is_emergency:
        severity = "EMERGENCY"
        hospitals = find_nearby_hospitals()
        emergency_msg = (
            "## 🚨 EMERGENCY ALERT\n\n"
            "Your symptoms may indicate a **life-threatening medical emergency**.\n\n"
            "### Immediate Actions:\n"
            f"- **Call emergency services immediately: {num}**\n"
            "- Do not drive yourself — call an ambulance\n"
            "- Stay calm and keep someone with you\n\n"
            f"### Nearby Hospitals:\n{hospitals}\n\n"
            "---\n"
            "*This AI cannot replace emergency medical care. Please seek help immediately.*"
        )

        if image_path:
            # Still analyze the image even in emergencies — append findings
            img_q = f"Emergency situation. {query or 'Analyze this medical image.'}"
            img_analysis = analyze_image_with_query(image_path, img_q)
            response = emergency_msg + "\n\n---\n\n### 🖼️ Image Analysis\n" + img_analysis
        else:
            response = emergency_msg

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

    return {
        "query":        query,
        "response":     response,
        "severity":     severity,
        "is_emergency": is_emergency,
        "hospitals":    hospitals,
    }
