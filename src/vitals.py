"""
Health Vitals Tracker
Stores readings in data/vitals.json with timestamp.
Each reading can include any subset of tracked metrics.
"""

import json
import os
from datetime import datetime

_FILE = os.path.join("data", "vitals.json")

# Configuration for each metric: label, unit, and thresholds
METRICS = {
    "systolic_bp": {
        "label": "Systolic BP", "unit": "mmHg", "min_val": 60, "max_val": 220,
        "normal": (90, 120), "warning": (121, 139), "danger_hi": 140,
        "color": "#FF6B6B",
    },
    "diastolic_bp": {
        "label": "Diastolic BP", "unit": "mmHg", "min_val": 40, "max_val": 140,
        "normal": (60, 80), "warning": (81, 89), "danger_hi": 90,
        "color": "#FFA040",
    },
    "glucose": {
        "label": "Blood Glucose (fasting)", "unit": "mg/dL", "min_val": 50, "max_val": 500,
        "normal": (70, 99), "warning": (100, 125), "danger_hi": 126,
        "color": "#E5B000",
    },
    "heart_rate": {
        "label": "Heart Rate", "unit": "bpm", "min_val": 30, "max_val": 220,
        "normal": (60, 100), "warning": (50, 59), "danger_hi": 101,
        "color": "#3FB950",
    },
    "weight": {
        "label": "Weight", "unit": "kg", "min_val": 20, "max_val": 300,
        "normal": None, "warning": None, "danger_hi": None,
        "color": "#58A6FF",
    },
    "spo2": {
        "label": "SpO₂ (Oxygen)", "unit": "%", "min_val": 50, "max_val": 100,
        "normal": (95, 100), "warning": (90, 94), "danger_hi": None,
        "color": "#39D0FF",
    },
}


def status(key: str, value: float) -> str:
    """Return 'normal', 'warning', or 'danger' for a given metric and value."""
    cfg = METRICS.get(key, {})
    n = cfg.get("normal")
    w = cfg.get("warning")
    dh = cfg.get("danger_hi")
    if not n:
        return "normal"
    if n[0] <= value <= n[1]:
        return "normal"
    if w and w[0] <= value <= w[1]:
        return "warning"
    if dh and value >= dh:
        return "danger"
    if value < n[0]:
        return "warning"
    return "normal"


def status_color(s: str) -> str:
    return {"normal": "#3FB950", "warning": "#E5B000", "danger": "#FF6B6B"}.get(s, "#8B949E")


def add_reading(values: dict) -> None:
    """Append a timestamped reading. values = {metric_key: float, ...}"""
    data = load_vitals()
    entry = {
        "timestamp":    datetime.now().isoformat(),
        "date_display": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }
    entry.update({k: v for k, v in values.items() if v is not None})
    data.append(entry)
    data = data[-180:]  # keep last 180 readings (~6 months daily)
    os.makedirs("data", exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_vitals() -> list:
    if not os.path.exists(_FILE):
        return []
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def clear_vitals() -> None:
    if os.path.exists(_FILE):
        os.remove(_FILE)


def latest(key: str) -> float | None:
    """Return the most recent reading for a metric, or None."""
    data = load_vitals()
    for entry in reversed(data):
        if key in entry:
            return entry[key]
    return None
