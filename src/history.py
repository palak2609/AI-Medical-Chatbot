import json
import os
from datetime import datetime

_FILE = os.path.join("data", "medical_history.json")


def save_session(messages: list, severity: str = "MILD") -> None:
    """Append the current session to the history file."""
    if not messages:
        return

    user_msgs  = [m["content"] for m in messages if m["role"] == "user"]
    ai_msgs    = [m["content"] for m in messages if m["role"] == "assistant"]

    entry = {
        "id":            datetime.now().strftime("%Y%m%d_%H%M%S"),
        "date_display":  datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "timestamp":     datetime.now().isoformat(),
        "main_complaint": (user_msgs[0] if user_msgs else "Unknown")[:150],
        "severity":      severity,
        "turns":         len(user_msgs),
        "ai_summary":    (ai_msgs[0] if ai_msgs else "")[:300],
    }

    history = load_history()
    history.insert(0, entry)   # newest first
    history = history[:50]     # keep last 50 sessions

    os.makedirs("data", exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def load_history() -> list:
    if not os.path.exists(_FILE):
        return []
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def clear_history() -> None:
    if os.path.exists(_FILE):
        os.remove(_FILE)
