import os
from groq import Groq

_EMERGENCY_KW = [
    "chest pain", "heart attack", "cardiac arrest", "stroke",
    "difficulty breathing", "can't breathe", "unconscious",
    "severe bleeding", "seizure", "anaphylaxis", "overdose",
]
_SEVERE_KW = [
    "high fever", "vomiting blood", "severe pain", "fainting",
    "convulsion", "paralysis", "severe burn", "blood in urine",
    "sudden vision loss", "sudden hearing loss",
]
_MODERATE_KW = [
    "headache", "fever", "cough", "infection", "stomach pain",
    "nausea", "vomiting", "diarrhea", "rash", "joint pain",
    "sore throat", "back pain", "dizziness",
]

_LEVELS = ["EMERGENCY", "SEVERE", "MODERATE", "MILD"]


def detect_severity(text: str) -> str:
    text_lower = text.lower()

    for kw in _EMERGENCY_KW:
        if kw in text_lower:
            return "EMERGENCY"
    for kw in _SEVERE_KW:
        if kw in text_lower:
            return "SEVERE"

    # LLM pass for nuanced classification
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical triage AI. "
                        "Classify the severity of the described symptoms. "
                        "Reply with ONLY one word: EMERGENCY, SEVERE, MODERATE, or MILD."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=5,
            temperature=0,
        )
        result = resp.choices[0].message.content.strip().upper()
        for level in _LEVELS:
            if level in result:
                return level
    except Exception:
        pass

    # Keyword fallback for moderate
    for kw in _MODERATE_KW:
        if kw in text_lower:
            return "MODERATE"

    return "MILD"
