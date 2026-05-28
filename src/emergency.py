import os
from groq import Groq

# Only phrases that unambiguously indicate an ACTIVE, IMMEDIATE life threat.
# Deliberately narrow — borderline cases go to the LLM for nuanced judgement.
_EMERGENCY_KEYWORDS = [
    # Cardiac — active event phrasing only
    "heart attack", "cardiac arrest", "myocardial infarction",
    "crushing chest pain", "chest pain and sweating", "chest pain and arm",
    # Breathing — only when severe/complete
    "cannot breathe", "can't breathe", "stopped breathing",
    "choking", "throat closing", "throat swelling",
    # Neurological — sudden onset, severe
    "stroke", "facial droop",
    "sudden severe headache", "worst headache of my life",
    "sudden loss of vision", "sudden paralysis",
    # Consciousness
    "unconscious", "unresponsive", "no pulse", "not breathing",
    # Bleeding
    "severe bleeding", "blood spurting", "vomiting blood", "coughing blood",
    # Mental health crisis
    "suicidal", "suicide", "want to die", "kill myself",
    # Active seizure
    "having a seizure", "currently seizing", "epilepsy attack",
    # Burns / poisoning
    "severe burn", "chemical burn",
    "overdose", "drug overdose",
    "anaphylaxis", "severe allergic reaction",
    # Trauma
    "spinal injury",
]

# These phrases are NOT emergencies on their own — let the LLM decide
_COMMON_NON_EMERGENCY = [
    "mild chest pain", "slight chest tightness", "chest pain after eating",
    "a little short of breath", "slightly short of breath", "short of breath after exercise",
    "mild shortness of breath", "fainted earlier", "fainted yesterday",
    "mild headache", "regular headache", "tension headache",
    "feeling weak", "feeling tired", "feeling confused",
    "minor head injury", "bumped my head", "small cut",
    "mild pain",
]


def detect_emergency(text: str) -> bool:
    text_lower = text.lower()

    # Fast non-emergency override — bail early for clearly minor complaints
    for safe in _COMMON_NON_EMERGENCY:
        if safe in text_lower:
            return False

    # Fast emergency keyword match
    for kw in _EMERGENCY_KEYWORDS:
        if kw in text_lower:
            return True

    # LLM pass — only for ambiguous cases not caught by keywords
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict medical triage AI. "
                        "Say YES only if the situation is an ACTIVE, IMMEDIATE life-threatening emergency "
                        "where calling 112/911 RIGHT NOW could save a life — "
                        "examples: heart attack in progress, active stroke, severe anaphylaxis, "
                        "not breathing, uncontrolled severe bleeding, drug overdose. "
                        "Say NO for: general pain, mild symptoms, chronic conditions, past incidents, "
                        "'should see a doctor', non-urgent concerns. "
                        "When in doubt, say NO. "
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
