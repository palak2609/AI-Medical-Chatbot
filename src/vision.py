import os
import base64
from groq import Groq

_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_FALLBACK_MODEL = "llama-3.1-8b-instant"

_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def analyze_image_with_query(image_path, query):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime_type = _MIME.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    medical_prompt = (
        "You are an AI medical image analyst. Examine this medical image carefully.\n\n"
        f"Patient context / query: {query}\n\n"
        "Provide a structured analysis covering:\n"
        "1. Visual observations (what you see in the image)\n"
        "2. Possible medical conditions suggested by the image\n"
        "3. Recommended next steps or specialist to consult\n"
        "4. Any warning signs that need urgent attention\n\n"
        "Always remind the patient that this is preliminary AI analysis, "
        "not a clinical diagnosis."
    )

    try:
        response = client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": medical_prompt,
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content

    except Exception:
        # Fallback: text-only response acknowledging the image
        fallback_prompt = (
            f"A patient uploaded a medical image and asked: {query}\n\n"
            "Since direct image analysis is temporarily unavailable, provide general "
            "medical guidance based on the query. Note that image-based diagnosis "
            "requires a qualified medical professional."
        )
        response = client.chat.completions.create(
            model=_FALLBACK_MODEL,
            messages=[{"role": "user", "content": fallback_prompt}],
            max_tokens=512,
        )
        return (
            "_Note: Direct image analysis is temporarily unavailable. "
            "General guidance provided below._\n\n"
            + response.choices[0].message.content
        )
