import os
from groq import Groq

_EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "cardiac arrest",
    "difficulty breathing", "can't breathe", "cannot breathe", "shortness of breath",
    "unconscious", "unresponsive", "fainted",
    "stroke", "facial droop", "sudden numbness",
    "severe bleeding", "blood vomiting", "vomiting blood", "coughing blood",
    "suicidal", "suicide", "want to die", "kill myself",
    "seizure", "convulsion", "epilepsy attack",
    "paralysis", "sudden weakness", "sudden confusion",
    "severe burn", "chemical burn",
    "overdose", "drug overdose", "poisoning",
    "anaphylaxis", "severe allergic reaction",
    "head injury", "spinal injury",
]


def detect_emergency(text: str) -> bool:
    text_lower = text.lower()

    # Fast keyword pass
    for kw in _EMERGENCY_KEYWORDS:
        if kw in text_lower:
            return True

    # LLM pass for nuanced phrasing
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical triage AI. "
                        "Determine if the described situation is a life-threatening emergency "
                        "requiring immediate emergency services (112/911). "
                        "Reply with ONLY the single word YES or NO."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=3,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False
