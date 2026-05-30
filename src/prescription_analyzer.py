"""
Prescription Analyzer
======================
1. Sends prescription image to Llama 4 Scout vision model
2. Extracts medicine names and dosage instructions
3. For each medicine, queries the RAG knowledge base (WHO Formulary)
   to explain: purpose, standard dose, side effects, food interaction, warnings
"""

import os
import base64
from groq import Groq
from src.rag_pipeline import ask_rag

_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_TEXT_MODEL   = "llama-3.1-8b-instant"

_EXTRACT_PROMPT = """You are a medical AI that reads prescription images.

Look at this prescription and extract ALL medicines listed.
For each medicine return EXACTLY this format (one medicine per line):

MEDICINE: <name> | DOSE: <dose and frequency> | DURATION: <duration if mentioned>

Rules:
- Include generic name if visible (e.g. "Paracetamol" not just "Crocin")
- If dose is not visible write: DOSE: not specified
- If duration is not visible write: DURATION: not specified
- List every single medicine — do not skip any
- If you cannot read the prescription clearly, list what you can see

Only output the MEDICINE lines, nothing else."""

_EXPLAIN_PROMPT = """A patient has been prescribed: {medicine} ({dose}, {duration})

Using the medical knowledge provided, explain this medicine clearly to the patient.
Respond in this exact format:

**What it is:** [One sentence — what condition/purpose this medicine treats]
**How it works:** [Simple explanation in plain language, 1-2 sentences]
**Standard dosage:** [Typical adult dose from knowledge base, plus the prescribed dose above]
**Take with food?:** [Yes / No / Doesn't matter — and brief reason]
**Common side effects:** [3-4 bullet points, most common ones]
**Important warnings:** [Any interactions, contraindications, or red flags]
**Tip:** [One practical patient tip — e.g. "Don't skip doses even if you feel better"]"""

_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "webp": "image/webp",
}


def _base64_image(image_path: str) -> tuple[str, str]:
    ext  = image_path.rsplit(".", 1)[-1].lower()
    mime = _MIME.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode(), mime


def extract_medicines(image_path: str) -> list[dict]:
    """
    Use the vision model to extract medicines from a prescription image.
    Returns a list of dicts: [{name, dose, duration}, ...]
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    b64, mime = _base64_image(image_path)

    try:
        resp = client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text",      "text": _EXTRACT_PROMPT},
                ],
            }],
            max_tokens=600,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception:
        # Vision unavailable — try text-only fallback with description
        resp = client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "The patient uploaded a prescription image but vision analysis is temporarily unavailable. "
                    "Please return this exact line so the system can handle it gracefully:\n"
                    "MEDICINE: [Vision unavailable] | DOSE: not specified | DURATION: not specified"
                ),
            }],
            max_tokens=60,
        )
        raw = resp.choices[0].message.content.strip()

    medicines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.upper().startswith("MEDICINE:"):
            continue
        parts = [p.strip() for p in line.split("|")]
        name     = parts[0].replace("MEDICINE:", "").strip() if len(parts) > 0 else "Unknown"
        dose     = parts[1].replace("DOSE:", "").strip()     if len(parts) > 1 else "not specified"
        duration = parts[2].replace("DURATION:", "").strip() if len(parts) > 2 else "not specified"
        if name:
            medicines.append({"name": name, "dose": dose, "duration": duration})

    return medicines


def explain_medicine(name: str, dose: str, duration: str) -> dict:
    """
    Query the RAG knowledge base to explain a single medicine.
    Returns {explanation, sources}
    """
    query = f"What is {name}? What is it used for, dosage, side effects, and warnings?"
    rag   = ask_rag(query)

    # Use the RAG context + a focused prompt via Groq
    client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = rag["response"]  # already LLM-generated from RAG

    prompt = _EXPLAIN_PROMPT.format(
        medicine=name, dose=dose, duration=duration
    )

    resp = client.chat.completions.create(
        model=_TEXT_MODEL,
        messages=[
            {"role": "system", "content": f"Medical knowledge:\n{context}"},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=700,
        temperature=0.2,
    )

    return {
        "name":        name,
        "dose":        dose,
        "duration":    duration,
        "explanation": resp.choices[0].message.content.strip(),
        "sources":     rag["sources"],
    }


def analyze_prescription(image_path: str) -> dict:
    """
    Full pipeline: image → extract medicines → explain each → return results.
    Returns {medicines: [{name, dose, duration, explanation, sources}], count: int}
    """
    medicines = extract_medicines(image_path)

    if not medicines:
        return {
            "medicines": [],
            "count":     0,
            "error":     "No medicines could be extracted from the image. Make sure the prescription is clear and well-lit.",
        }

    explained = []
    for med in medicines:
        if "[Vision unavailable]" in med["name"]:
            explained.append({
                "name":        "[Vision unavailable]",
                "dose":        "—",
                "duration":    "—",
                "explanation": "Vision analysis is temporarily unavailable. Please try uploading as a clearer image or type the medicine name in the chat.",
                "sources":     [],
            })
        else:
            explained.append(explain_medicine(med["name"], med["dose"], med["duration"]))

    return {"medicines": explained, "count": len(explained)}
