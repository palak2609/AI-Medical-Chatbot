"""
Pre-built first-aid cards shown instantly when emergency keywords are detected.
No LLM call required — these appear before the AI response loads.
"""

CARDS = {
    "heart_attack": {
        "title": "Heart Attack",
        "icon": "🫀",
        "color": "#FF4B4B",
        "keywords": ["heart attack", "cardiac arrest", "chest pain", "myocardial"],
        "signs": [
            "Severe chest pain or pressure",
            "Pain spreading to arm, jaw, or neck",
            "Shortness of breath",
            "Cold sweat, nausea, lightheadedness",
        ],
        "steps": [
            "Call 112 immediately",
            "Have person sit or lie down comfortably",
            "Loosen tight clothing around neck and chest",
            "Give aspirin (325 mg) if available and not allergic",
            "Begin CPR if person becomes unconscious and stops breathing normally",
            "Use AED if one is available",
        ],
    },
    "stroke": {
        "title": "Stroke — Use FAST",
        "icon": "🧠",
        "color": "#FF8C00",
        "keywords": ["stroke", "facial droop", "arm weakness", "slurred speech", "sudden numbness"],
        "signs": [
            "F — Face drooping on one side",
            "A — Arm weakness (raise both arms — one drift down?)",
            "S — Speech slurred or strange",
            "T — Time to call 112 NOW",
        ],
        "steps": [
            "Call 112 immediately — every minute counts",
            "Note the exact time symptoms started",
            "Keep person calm, still, and comfortable",
            "Do NOT give food or water",
            "Lay on their side if unconscious",
            "Monitor breathing until help arrives",
        ],
    },
    "choking": {
        "title": "Choking",
        "icon": "🫁",
        "color": "#FF6B35",
        "keywords": ["choking", "airway blocked", "can't breathe", "heimlich"],
        "signs": [
            "Cannot speak, cough, or breathe",
            "Clutching throat with both hands",
            "Blue or purple lips / face",
            "High-pitched wheezing sounds",
        ],
        "steps": [
            "Ask 'Are you choking?' — if they can't reply, act immediately",
            "Give 5 firm back blows between shoulder blades with heel of hand",
            "Give 5 abdominal thrusts (Heimlich maneuver) — push inward and upward",
            "Alternate 5 back blows and 5 thrusts until object dislodges",
            "If unconscious: call 112 and begin CPR",
            "For infants under 1 year: use 5 back blows + 5 chest thrusts only",
        ],
    },
    "severe_burn": {
        "title": "Severe Burn",
        "icon": "🔥",
        "color": "#E55B2B",
        "keywords": ["severe burn", "chemical burn", "fire burn", "major burn"],
        "signs": [
            "Large area of burned skin (larger than palm)",
            "White, brown, or black charred / leathery skin",
            "Severe pain or complete absence of pain (3rd degree)",
            "Blistering, swelling, or open wounds",
        ],
        "steps": [
            "Call 112 for severe or large burns",
            "Cool burn under cool (NOT cold/iced) running water for 20 minutes",
            "Remove jewelry and loose clothing near burn — NOT if stuck to skin",
            "Cover loosely with cling film or clean non-fluffy cloth",
            "Do NOT use ice, butter, toothpaste, or any cream",
            "Do NOT pop blisters",
        ],
    },
    "seizure": {
        "title": "Seizure",
        "icon": "⚡",
        "color": "#9B59B6",
        "keywords": ["seizure", "convulsion", "epilepsy attack", "fits"],
        "signs": [
            "Uncontrolled shaking or jerking of body",
            "Loss of consciousness or awareness",
            "Staring blankly into space",
            "Temporary confusion after the episode",
        ],
        "steps": [
            "Stay calm and start timing the seizure",
            "Clear the area of sharp or dangerous objects",
            "Gently cushion the person's head with something soft",
            "Turn person gently on their side to prevent choking",
            "Do NOT restrain their movements",
            "Do NOT put anything in their mouth",
            "Call 112 if: first-ever seizure, lasts > 5 minutes, or person doesn't recover",
        ],
    },
    "unconscious": {
        "title": "Unconscious Person",
        "icon": "😵",
        "color": "#E74C3C",
        "keywords": ["unconscious", "unresponsive", "fainted", "passed out", "not waking"],
        "signs": [
            "Not responding to voice or touch",
            "No voluntary movement",
            "Abnormal, slow, or absent breathing",
        ],
        "steps": [
            "Check response — tap shoulders firmly and shout their name",
            "Call 112 immediately",
            "Check breathing: look, listen, feel for up to 10 seconds",
            "If not breathing normally, begin CPR — 30 chest compressions + 2 rescue breaths",
            "Continue CPR until help arrives or person recovers",
            "Use AED as soon as one is available",
        ],
    },
}


def get_card(text: str) -> dict | None:
    """Return the first matching first-aid card for the given text, or None."""
    text_lower = text.lower()
    for card in CARDS.values():
        for kw in card["keywords"]:
            if kw in text_lower:
                return card
    return None


def all_cards() -> list:
    return list(CARDS.values())


def render_html(card: dict) -> str:
    """Return an HTML string for rendering the card in Streamlit."""
    color = card["color"]
    signs_li = "".join(f"<li>{s}</li>" for s in card["signs"])
    steps_ol = "".join(f"<li>{s}</li>" for s in card["steps"])
    return f"""
<div style="
    background:{color}18;
    border-left:4px solid {color};
    border-radius:10px;
    padding:16px 20px;
    margin:8px 0 16px;
">
  <h3 style="color:{color};margin:0 0 10px 0;font-size:17px">
    {card['icon']} {card['title']} — First Aid
  </h3>
  <p style="color:#E6EDF3;font-weight:600;margin:6px 0 2px">Warning Signs:</p>
  <ul style="color:#C9D1D9;margin:0 0 8px 18px;line-height:1.7">{signs_li}</ul>
  <p style="color:#E6EDF3;font-weight:600;margin:6px 0 2px">Steps to Follow:</p>
  <ol style="color:#C9D1D9;margin:0 0 0 18px;line-height:1.7">{steps_ol}</ol>
</div>
"""
