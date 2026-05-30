"""
Input validator — catches gibberish before the RAG pipeline runs.
Two-layer approach:
  1. Fast heuristics (no API call)
  2. LLM judge for borderline cases (tiny prompt, max_tokens=3)
"""

import os
import re
from groq import Groq

_FRIENDLY_ERROR = (
    "I couldn't understand your message. "
    "Please describe your symptoms or health question in clear words.\n\n"
    "*Example: \"I have a fever of 101°F and a headache since yesterday\"*"
)


def _alpha_ratio(text: str) -> float:
    """Fraction of characters that are letters or spaces."""
    if not text:
        return 0.0
    return sum(c.isalpha() or c.isspace() for c in text) / len(text)


# Known 5-char keyboard-row sequences — only actual keyboard mashing produces these
_KB_SEQS = [
    # Row 1 runs
    "qwert","werty","ertyu","rtyui","tyuio","yuiop",
    # Row 2 runs
    "asdfg","sdfgh","dfghj","fghjk","ghjkl",
    # Row 3 runs
    "zxcvb","xcvbn","cvbnm",
]

def _contains_keyboard_run(text: str) -> bool:
    """True if text contains a 5+ char keyboard-row sequence."""
    t = text.lower()
    return any(seq in t for seq in _KB_SEQS)


def _has_no_vowels(word: str) -> bool:
    """True if a word contains zero vowels (unambiguously gibberish)."""
    vowels = set("aeiouAEIOU")
    letters = [c for c in word if c.isalpha()]
    if len(letters) < 2:
        return False
    return not any(c in vowels for c in letters)


def _quick_reject(text: str) -> str | None:
    """
    Return an error string if the text is obviously invalid, else None.
    No API call — instant.
    """
    text = text.strip()

    if len(text) < 4:
        return "Please type your health question or describe your symptoms."

    # Mostly non-alpha (e.g. "12345!!! @@@")
    if _alpha_ratio(text) < 0.55:
        return _FRIENDLY_ERROR

    # Keyboard-row run detection (e.g. "qwerty", "asdfghjkl")
    if _contains_keyboard_run(text):
        return _FRIENDLY_ERROR

    words = [w for w in re.split(r'\W+', text) if len(w) >= 2]
    if len(words) >= 2:
        # ≥40% of words have zero vowels → gibberish (e.g. "ctfcr hv huvb ubv")
        no_vowel_count = sum(_has_no_vowels(w) for w in words)
        if no_vowel_count / len(words) >= 0.40:
            return _FRIENDLY_ERROR

    return None


def is_valid_query(text: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    error_message is empty string when valid.
    """
    text = (text or "").strip()

    # Layer 1: quick heuristics
    quick_err = _quick_reject(text)
    if quick_err:
        return False, quick_err

    # Layer 2: LLM judge for borderline cases
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict query validator for a medical AI assistant. "
                        "Reply YES only if the text is a clear, meaningful health or medical query. "
                        "Reply NO if it is: gibberish, random characters, keyboard mashing "
                        "(e.g. 'asdfjkl qwerty', 'ctfcr hv', 'nvbncv mnc'), "
                        "nonsense words, or completely unrelated to health. "
                        "If in doubt, reply NO. "
                        "Reply ONLY the single word YES or NO."
                    ),
                },
                {
                    "role": "user",
                    "content": f'Validate: "{text[:300]}"',
                },
            ],
            max_tokens=3,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().upper()
        if answer.startswith("NO"):
            return False, _FRIENDLY_ERROR
    except Exception:
        pass  # If LLM fails, let query through — don't block valid users

    return True, ""
