"""
Food & Calorie Analyzer
=======================
Accepts either a text description of a meal or a food photo.
Returns calories, macros, health rating, and personalised tips.
"""

import os
import base64
from groq import Groq

_TEXT_MODEL   = "llama-3.1-8b-instant"
_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "webp": "image/webp",
}

_ANALYSIS_PROMPT = """You are a nutritionist AI. Analyze this meal and respond in EXACTLY this format:

CALORIES: [number only, e.g. 420]
PROTEIN: [number in grams, e.g. 18]
CARBS: [number in grams, e.g. 55]
FAT: [number in grams, e.g. 12]
FIBER: [number in grams, e.g. 6]
RATING: [HEALTHY or MODERATE or UNHEALTHY]

**What you ate:** [One sentence identifying the food items]

**Nutritional highlights:** [2-3 bullet points on what's good about this meal]

**What to improve:** [2-3 specific, actionable suggestions]

**Better alternatives:** [One practical swap or addition to make this meal healthier]

**Tip for you:** [A personalised tip based on the patient profile: {profile}]

---
*Calorie estimates are approximate. Actual values vary by portion size and preparation method.*"""


def _profile_str(profile: dict) -> str:
    parts = []
    if profile.get("age"):        parts.append(f"age {profile['age']}")
    if profile.get("conditions"): parts.append(profile["conditions"])
    return ", ".join(parts) if parts else "general adult"


def _parse_response(raw: str) -> dict:
    """Extract structured fields from the LLM response."""
    result = {
        "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0,
        "rating": "MODERATE", "text": "",
    }
    lines = raw.splitlines()
    text_lines = []
    for line in lines:
        line = line.strip()
        for field in ("CALORIES", "PROTEIN", "CARBS", "FAT", "FIBER"):
            if line.upper().startswith(field + ":"):
                try:
                    result[field.lower()] = int(line.split(":", 1)[1].strip().split()[0])
                except Exception:
                    pass
                break
        else:
            if line.upper().startswith("RATING:"):
                r = line.split(":", 1)[1].strip().upper()
                if "HEALTHY" in r and "UN" not in r:
                    result["rating"] = "HEALTHY"
                elif "UNHEALTHY" in r:
                    result["rating"] = "UNHEALTHY"
                else:
                    result["rating"] = "MODERATE"
            else:
                text_lines.append(line)

    result["text"] = "\n".join(text_lines).strip()
    return result


def analyze_food_text(description: str, profile: dict | None = None) -> dict:
    """Analyze a text description of a meal."""
    profile = profile or {}
    prompt = f"The patient ate: {description}\n\n" + _ANALYSIS_PROMPT.format(
        profile=_profile_str(profile)
    )
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    resp = client.chat.completions.create(
        model=_TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.2,
    )
    return _parse_response(resp.choices[0].message.content)


def analyze_food_photo(image_path: str, profile: dict | None = None) -> dict:
    """Analyze a photo of food using the vision model."""
    profile = profile or {}
    ext  = image_path.rsplit(".", 1)[-1].lower()
    mime = _MIME.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    prompt = "Look at this food image and analyze the meal.\n\n" + _ANALYSIS_PROMPT.format(
        profile=_profile_str(profile)
    )
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    try:
        resp = client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text",      "text": prompt},
                ],
            }],
            max_tokens=700,
            temperature=0.2,
        )
        return _parse_response(resp.choices[0].message.content)
    except Exception:
        # Fallback to text-only
        return analyze_food_text("a meal shown in the uploaded photo", profile)
