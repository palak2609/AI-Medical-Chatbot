"""
Medical report analyzer.
- PDF reports  → extract text with pypdf, then send to Groq LLM
- Image reports → send to Groq vision model (same as vision.py)
"""

import os
import base64
from groq import Groq

_LLM_MODEL    = "llama-3.1-8b-instant"
_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_ANALYSIS_PROMPT = """You are an expert medical AI specializing in interpreting medical reports and laboratory results.

Analyze the provided medical report and respond in this exact structured format:

## 📋 Report Type
Identify what kind of report this is (e.g. CBC blood test, lipid panel, liver function, kidney function, thyroid panel, urine analysis, X-ray report, prescription, doctor's note, etc.)

## 🔍 Key Findings
List every value or finding mentioned. For lab tests use this format:
| Parameter | Result | Normal Range | Status |
|---|---|---|---|
| e.g. Hemoglobin | 11.2 g/dL | 13.5–17.5 g/dL | 🔴 LOW |

Use ✅ NORMAL, 🟡 BORDERLINE, 🔴 LOW, 🔴 HIGH as status labels.

## ⚠️ Abnormal Values
List only the out-of-range values and explain in simple language what each one means for the patient's health.

## 🩺 Overall Assessment
A 2–3 sentence plain-language summary of what this report suggests about the patient's current health.

## ✅ Recommended Actions
Concrete steps the patient should take (e.g. repeat test in X weeks, dietary changes, see a specialist).

## ❓ Questions to Ask Your Doctor
3–5 specific questions the patient should bring up at their next appointment based on these results.

---
⚠️ *This is AI-assisted interpretation for educational purposes. Always verify with a qualified doctor before making any medical decisions.*
"""

_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "webp": "image/webp",
}


def _extract_pdf_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages).strip()


def analyze_pdf(pdf_path: str) -> str:
    """Extract text from PDF and analyze with LLM."""
    text = _extract_pdf_text(pdf_path)

    if not text:
        return (
            "⚠️ Could not extract text from this PDF. "
            "It may be a scanned image. Try uploading it as an image (JPG/PNG) instead."
        )

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    resp = client.chat.completions.create(
        model=_LLM_MODEL,
        messages=[
            {"role": "system", "content": _ANALYSIS_PROMPT},
            {"role": "user",   "content": f"Here is the medical report:\n\n{text[:6000]}"},
        ],
        max_tokens=2048,
    )
    return resp.choices[0].message.content


def analyze_image_report(image_path: str) -> str:
    """Analyze a scanned / photographed medical report via Groq vision."""
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = _MIME.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    try:
        resp = client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": _ANALYSIS_PROMPT,
                        },
                    ],
                }
            ],
            max_tokens=2048,
        )
        return resp.choices[0].message.content

    except Exception:
        # Fallback: text-only with description
        resp = client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[
                {"role": "system", "content": _ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "The patient has uploaded a scanned medical report image. "
                        "Vision analysis is temporarily unavailable. "
                        "Please explain what information a patient should typically look for "
                        "in a medical report and how to interpret common lab values."
                    ),
                },
            ],
            max_tokens=1024,
        )
        return (
            "_Note: Direct image analysis is temporarily unavailable._\n\n"
            + resp.choices[0].message.content
        )
