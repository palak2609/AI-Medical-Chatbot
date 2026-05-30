"""
Drug Interaction Checker
Uses the RAG knowledge base (WHO Formulary) + LLM to check
whether two drugs interact and how serious it is.
"""

import os
from groq import Groq
from src.rag_pipeline import ask_rag

_MODEL = "llama-3.1-8b-instant"

_SEVERITY_LEVELS = {
    "none":             ("No known interaction", "#3FB950"),
    "mild":             ("Mild interaction",     "#58A6FF"),
    "moderate":         ("Moderate interaction", "#E5B000"),
    "severe":           ("Severe interaction",   "#FFA040"),
    "contraindicated":  ("Contraindicated",      "#FF6B6B"),
    "unknown":          ("Unknown",              "#8B949E"),
}

_PROMPT = """A patient wants to know if it is safe to take these two medicines together:

Drug 1: {drug1}
Drug 2: {drug2}

Medical knowledge available:
{context}

Respond in this EXACT format:

SEVERITY: [none / mild / moderate / severe / contraindicated / unknown]

**Interaction Summary:** [One clear sentence stating if it is safe or not]

**What happens when combined:** [2-3 sentences explaining the mechanism or effect]

**Who is most at risk:** [Groups that should be especially careful]

**What to do:** [Practical advice — can they take both, what spacing, what alternatives, should they ask their doctor]

---
*Always confirm with your doctor or pharmacist before changing medications.*"""


def check_interaction(drug1: str, drug2: str) -> dict:
    """
    Check interaction between two drugs.
    Returns: {severity, severity_label, color, explanation}
    """
    drug1 = drug1.strip()
    drug2 = drug2.strip()

    # RAG query for relevant knowledge
    query    = f"drug interaction between {drug1} and {drug2}"
    rag_resp = ask_rag(query)
    context  = rag_resp["response"]
    sources  = rag_resp["sources"]

    # LLM analysis
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = _PROMPT.format(drug1=drug1, drug2=drug2, context=context[:3000])

    resp = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()

    # Parse severity from first line
    severity = "unknown"
    lines    = raw.splitlines()
    for line in lines[:3]:
        if line.upper().startswith("SEVERITY:"):
            sev_raw = line.split(":", 1)[1].strip().lower()
            for key in _SEVERITY_LEVELS:
                if key in sev_raw:
                    severity = key
                    break
            break

    # Remove the SEVERITY line from the explanation
    explanation = "\n".join(l for l in lines if not l.upper().startswith("SEVERITY:")).strip()

    label, color = _SEVERITY_LEVELS.get(severity, _SEVERITY_LEVELS["unknown"])

    return {
        "drug1":       drug1,
        "drug2":       drug2,
        "severity":    severity,
        "label":       label,
        "color":       color,
        "explanation": explanation,
        "sources":     sources,
    }
