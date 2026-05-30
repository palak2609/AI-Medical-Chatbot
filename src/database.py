"""
Database abstraction layer — crash-proof dual backend.

Primary  : Supabase PostgreSQL (cloud, SUPABASE_URL + SUPABASE_KEY in .env)
Fallback : SQLite local file   (data/medical_app.db)

All public functions silently fall back to SQLite if Supabase is unreachable.
The app never crashes due to a DB failure — worst case it uses local storage.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime

_SQLITE_PATH = os.path.join("data", "medical_app.db")

# ── SQLite bootstrap (always available) ────────────────────────────────────────
def _boot_sqlite():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            name          TEXT DEFAULT '',
            age           TEXT DEFAULT '',
            blood_group   TEXT DEFAULT '',
            conditions    TEXT DEFAULT '',
            created_at    TEXT
        );
        CREATE TABLE IF NOT EXISTS consultations (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            session_id TEXT,
            messages   TEXT,
            severity   TEXT DEFAULT 'MILD',
            city       TEXT DEFAULT '',
            timestamp  TEXT
        );
        CREATE TABLE IF NOT EXISTS vitals (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            timestamp    TEXT,
            systolic_bp  REAL,
            diastolic_bp REAL,
            glucose      REAL,
            heart_rate   REAL,
            weight       REAL,
            spo2         REAL
        );
        CREATE TABLE IF NOT EXISTS prescriptions (
            id        TEXT PRIMARY KEY,
            user_id   TEXT NOT NULL,
            timestamp TEXT,
            medicines TEXT
        );
    """)
    conn.commit()
    conn.close()


_boot_sqlite()

# ── Supabase client (optional) ─────────────────────────────────────────────────
_sb = None
_cloud = False


def _init_supabase() -> bool:
    global _sb, _cloud
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        return False
    try:
        from supabase import create_client
        _sb = create_client(url, key)
        # Quick connectivity test
        _sb.table("users").select("id").limit(1).execute()
        _cloud = True
        return True
    except Exception:
        _sb   = None
        _cloud = False
        return False


_init_supabase()


def is_cloud() -> bool:
    return _cloud


def reconnect() -> bool:
    """Try to reconnect to Supabase — call this to refresh after a network blip."""
    return _init_supabase()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _uid()  -> str: return str(uuid.uuid4())
def _now()  -> str: return datetime.now().isoformat()
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_SQLITE_PATH)
    c.row_factory = sqlite3.Row
    return c


def _clean_messages(messages: list) -> list:
    """Strip binary fields (audio_bytes) before JSON serialisation."""
    safe = []
    for m in messages:
        safe.append({k: v for k, v in m.items()
                     if k != "audio_bytes" and isinstance(v, (str, int, float, bool, list, dict, type(None)))})
    return safe


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_user(username: str) -> dict | None:
    if _cloud:
        try:
            r = _sb.table("users").select("*").eq("username", username).execute()
            return r.data[0] if r.data else None
        except Exception:
            pass
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def create_user(username: str, email: str, password_hash: str,
                name: str, age: str, blood_group: str, conditions: str) -> dict:
    user = {
        "id": _uid(), "username": username, "email": email,
        "password_hash": password_hash, "name": name, "age": age,
        "blood_group": blood_group, "conditions": conditions,
        "created_at": _now(),
    }
    if _cloud:
        try:
            _sb.table("users").insert(user).execute()
            return user
        except Exception:
            pass
    with _conn() as c:
        c.execute("""
            INSERT INTO users (id,username,email,password_hash,name,age,blood_group,conditions,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, tuple(user.values()))
        c.commit()
    return user


def update_profile(user_id: str, name: str, age: str, blood_group: str, conditions: str):
    data = {"name": name, "age": age, "blood_group": blood_group, "conditions": conditions}
    if _cloud:
        try:
            _sb.table("users").update(data).eq("id", user_id).execute()
            return
        except Exception:
            pass
    with _conn() as c:
        c.execute("UPDATE users SET name=?,age=?,blood_group=?,conditions=? WHERE id=?",
                  (name, age, blood_group, conditions, user_id))
        c.commit()


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTATION OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_consultation(user_id: str, session_id: str, messages: list,
                      severity: str, city: str):
    msgs_json = json.dumps(_clean_messages(messages), ensure_ascii=False)
    record = {
        "id": session_id, "user_id": user_id, "session_id": session_id,
        "messages": msgs_json, "severity": severity,
        "city": city, "timestamp": _now(),
    }
    if _cloud:
        try:
            _sb.table("consultations").upsert(record).execute()
            return
        except Exception:
            pass
    with _conn() as c:
        c.execute("""
            INSERT INTO consultations (id,user_id,session_id,messages,severity,city,timestamp)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                messages=excluded.messages, severity=excluded.severity,
                timestamp=excluded.timestamp
        """, (session_id, user_id, session_id, msgs_json, severity, city, record["timestamp"]))
        c.commit()


def get_consultations(user_id: str, limit: int = 20) -> list:
    if _cloud:
        try:
            r = (_sb.table("consultations").select("id,severity,city,timestamp,messages")
                 .eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute())
            return r.data
        except Exception:
            pass
    with _conn() as c:
        rows = c.execute(
            "SELECT id,severity,city,timestamp,messages FROM consultations "
            "WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# VITALS OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_vital(user_id: str, readings: dict):
    record = {"id": _uid(), "user_id": user_id, "timestamp": _now()}
    record.update({k: v for k, v in readings.items() if v is not None})
    if _cloud:
        try:
            _sb.table("vitals").insert(record).execute()
            return
        except Exception:
            pass
    cols = list(record.keys())
    with _conn() as c:
        c.execute(
            f"INSERT INTO vitals ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
            list(record.values())
        )
        c.commit()


def get_vitals(user_id: str, limit: int = 180) -> list:
    if _cloud:
        try:
            r = (_sb.table("vitals").select("*")
                 .eq("user_id", user_id).order("timestamp", desc=False).limit(limit).execute())
            return r.data
        except Exception:
            pass
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM vitals WHERE user_id=? ORDER BY timestamp ASC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_prescription(user_id: str, medicines: list):
    record = {
        "id": _uid(), "user_id": user_id,
        "timestamp": _now(),
        "medicines": json.dumps(medicines, ensure_ascii=False),
    }
    if _cloud:
        try:
            _sb.table("prescriptions").insert(record).execute()
            return
        except Exception:
            pass
    with _conn() as c:
        c.execute("INSERT INTO prescriptions (id,user_id,timestamp,medicines) VALUES (?,?,?,?)",
                  (record["id"], user_id, record["timestamp"], record["medicines"]))
        c.commit()


def get_prescriptions(user_id: str, limit: int = 20) -> list:
    if _cloud:
        try:
            r = (_sb.table("prescriptions").select("*")
                 .eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute())
            return r.data
        except Exception:
            pass
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM prescriptions WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]
