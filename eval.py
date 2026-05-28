"""
Ablation Study: RAG Pipeline vs Plain LLM
==========================================
Tests 20 medical questions and compares response quality.
Uses LLM-as-judge (Groq LLaMA) to score both approaches 1-5.

Run:  python eval.py
Output: data/eval_results.json  (loaded automatically in the app's Evaluation tab)
Time:   ~5-8 minutes (API calls for 20 questions x 2 modes + 20 judge calls)
"""

import os
import json
import time
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from groq import Groq

# ── 20 test questions across 5 categories ─────────────────────────────────────
QUESTIONS = [
    # Common diseases
    {"category": "Common Diseases", "question": "What are the symptoms and treatment for dengue fever?"},
    {"category": "Common Diseases", "question": "How is typhoid fever diagnosed and treated?"},
    {"category": "Common Diseases", "question": "What causes malaria and what medicines are used to treat it?"},
    {"category": "Common Diseases", "question": "What are the early warning signs of type 2 diabetes?"},

    # Medicines & dosages
    {"category": "Medicines & Dosages", "question": "What is the standard adult dosage of paracetamol and when should it not be used?"},
    {"category": "Medicines & Dosages", "question": "What is amoxicillin used for and what are its common side effects?"},
    {"category": "Medicines & Dosages", "question": "What medicines are used to treat hypertension and how do they work?"},
    {"category": "Medicines & Dosages", "question": "What is metformin and why is it prescribed for diabetes?"},

    # India-specific health
    {"category": "India-Specific Health", "question": "How can I prevent waterborne diseases during monsoon season?"},
    {"category": "India-Specific Health", "question": "What are the symptoms of chikungunya and how is it managed?"},
    {"category": "India-Specific Health", "question": "What is the treatment for severe dehydration from diarrhea?"},
    {"category": "India-Specific Health", "question": "What foods should a diabetic patient in India avoid?"},

    # Clinical guidance
    {"category": "Clinical Guidance", "question": "When should a patient with chest pain go to emergency versus wait for a doctor?"},
    {"category": "Clinical Guidance", "question": "What are the normal ranges for blood pressure, blood sugar, and cholesterol?"},
    {"category": "Clinical Guidance", "question": "What specialist should a patient see for persistent lower back pain?"},
    {"category": "Clinical Guidance", "question": "How is asthma managed in adults and what triggers should be avoided?"},

    # Lifestyle & prevention
    {"category": "Lifestyle & Prevention", "question": "What dietary changes help reduce high cholesterol?"},
    {"category": "Lifestyle & Prevention", "question": "What are the signs of iron deficiency anaemia and how is it treated?"},
    {"category": "Lifestyle & Prevention", "question": "How much sleep do adults need and what are the health effects of sleep deprivation?"},
    {"category": "Lifestyle & Prevention", "question": "What vaccinations are recommended for adults in India?"},
]

_JUDGE_PROMPT = """You are a medical education expert evaluating AI medical assistant responses.

Score this response on a scale of 1-5 for each dimension:
- Accuracy (1=wrong/dangerous, 5=medically correct)
- Specificity (1=vague generic answer, 5=specific with drug names/dosages/timelines)
- Grounding (1=pure hallucination, 5=clearly references established medical knowledge)

Final score = average of the three.

Question: {question}
Response: {response}

Reply ONLY in this exact JSON format (no other text):
{{"accuracy": X, "specificity": X, "grounding": X, "score": X.X, "note": "one sentence summary"}}"""


def _call_llm(messages: list, model: str = "llama-3.1-8b-instant", max_tokens: int = 600) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def _rag_response(question: str) -> tuple[str, list[str]]:
    """Get response from the full RAG pipeline."""
    from src.rag_pipeline import ask_rag
    result = ask_rag(question)
    return result["response"], result["sources"]


def _llm_response(question: str) -> str:
    """Get response from plain LLM with no knowledge base."""
    return _call_llm([
        {
            "role": "system",
            "content": (
                "You are a medical assistant. Answer the patient's question. "
                "You do NOT have access to any external knowledge base or documents."
            ),
        },
        {"role": "user", "content": question},
    ])


def _judge(question: str, response: str) -> dict:
    """Score a response using LLM-as-judge."""
    prompt = _JUDGE_PROMPT.format(question=question, response=response[:2000])
    raw = _call_llm(
        [{"role": "user", "content": prompt}],
        max_tokens=150,
    )
    try:
        # Extract JSON from response
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"accuracy": 3, "specificity": 3, "grounding": 3, "score": 3.0, "note": "Parse error"}


def run_evaluation():
    print(f"Running evaluation on {len(QUESTIONS)} questions...")
    print("This will take ~5-8 minutes.\n")

    results = []
    total_rag = 0
    total_llm = 0

    for i, q in enumerate(QUESTIONS, 1):
        question = q["question"]
        category = q["category"]
        print(f"[{i:02d}/{len(QUESTIONS)}] {category}: {question[:60]}...")

        # RAG response
        print("       Getting RAG response...", end="\r")
        try:
            rag_resp, sources = _rag_response(question)
        except Exception as e:
            rag_resp = f"Error: {e}"
            sources  = []
        time.sleep(1)  # rate limit buffer

        # Plain LLM response
        print("       Getting LLM response...", end="\r")
        try:
            llm_resp = _llm_response(question)
        except Exception as e:
            llm_resp = f"Error: {e}"
        time.sleep(1)

        # Judge RAG response
        print("       Judging RAG...          ", end="\r")
        rag_judge = _judge(question, rag_resp)
        time.sleep(1)

        # Judge plain LLM response
        print("       Judging LLM...          ", end="\r")
        llm_judge = _judge(question, llm_resp)
        time.sleep(1)

        rag_score = round(rag_judge.get("score", 3.0), 1)
        llm_score = round(llm_judge.get("score", 3.0), 1)
        total_rag += rag_score
        total_llm += llm_score

        winner = "RAG" if rag_score >= llm_score else "LLM"
        print(f"       RAG: {rag_score}/5  LLM: {llm_score}/5  Winner: {winner}       ")

        results.append({
            "category":    category,
            "question":    question,
            "rag_score":   rag_score,
            "llm_score":   llm_score,
            "sources":     sources,
            "rag_note":    rag_judge.get("note", ""),
            "llm_note":    llm_judge.get("note", ""),
            "rag_response": rag_resp[:500],
            "llm_response": llm_resp[:500],
        })

    n = len(QUESTIONS)
    avg_rag = round(total_rag / n, 2)
    avg_llm = round(total_llm / n, 2)
    improvement = round((avg_rag - avg_llm) / avg_llm * 100, 1) if avg_llm else 0
    rag_wins = sum(1 for r in results if r["rag_score"] >= r["llm_score"])

    summary = {
        "avg_rag_score":     avg_rag,
        "avg_llm_score":     avg_llm,
        "improvement_pct":   improvement,
        "rag_wins":          rag_wins,
        "llm_wins":          n - rag_wins,
        "total_questions":   n,
        "knowledge_sources": [
            "Gale Encyclopedia of Medicine",
            "WHO Essential Medicines List (2023)",
            "WHO Model Formulary",
        ],
        "model":             "llama-3.1-8b-instant (Groq)",
        "embedding_model":   "sentence-transformers/all-MiniLM-L6-v2",
        "vector_db":         "Pinecone Serverless",
    }

    output = {"summary": summary, "results": results}
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "eval_results.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*55}")
    print(f"  EVALUATION COMPLETE")
    print(f"{'='*55}")
    print(f"  RAG Pipeline avg score : {avg_rag}/5")
    print(f"  Plain LLM avg score    : {avg_llm}/5")
    print(f"  RAG improvement        : +{improvement}%")
    print(f"  RAG wins               : {rag_wins}/{n} questions")
    print(f"{'='*55}")
    print(f"  Results saved to data/eval_results.json")
    print(f"  Open the app Evaluation tab to see the full breakdown.")


if __name__ == "__main__":
    run_evaluation()
