"""
Sample Data Seeder
==================
Creates 3 test users with realistic medical histories, vitals, and consultations.
Run once after setting up the database (Supabase or SQLite).

Usage:
    python seed.py

Test accounts created:
    Username: rahul_sharma   Password: rahul123
    Username: priya_patel    Password: priya123
    Username: demo           Password: demo123
"""

import json
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
from src.auth import hash_password
from src.database import (
    get_user, create_user, save_consultation,
    save_vital, save_prescription, is_cloud, _uid, _conn
)
import sqlite3, os

print(f"Database mode: {'Supabase Cloud' if is_cloud() else 'SQLite Local'}")
print("Seeding sample data...\n")


# ── Helpers ───────────────────────────────────────────────────────────────────

def ts(days_ago: int = 0, hour: int = 10) -> str:
    """ISO timestamp N days ago."""
    return (datetime.now() - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0).isoformat()


def make_messages(complaint: str, ai_response: str) -> list:
    return [
        {"role": "user",      "content": complaint},
        {"role": "assistant", "content": ai_response, "severity": "MODERATE",
         "sources": ["Gale Encyclopedia of Medicine", "WHO Model Formulary"]},
    ]


# ── Sample AI responses ───────────────────────────────────────────────────────

FEVER_RESPONSE = """**Possible Condition:** Viral fever / Influenza

**Symptoms Identified:**
- High body temperature (above 38°C)
- Body ache and fatigue
- Possible chills and sweating

**Common Treatments & Medicines:**
- Paracetamol (Crocin/Dolo 650) — 500–1000 mg every 6 hours to reduce fever; max 4g/day
- Ibuprofen (Brufen) — 400 mg every 8 hours if paracetamol is insufficient; take with food
- ORS (Oral Rehydration Solution) — to prevent dehydration

**Recommended Precautions:**
- Drink 2–3 litres of water/fluids daily
- Rest completely; avoid physical exertion
- Light diet — soups, khichdi, fruits
- Monitor temperature every 4–6 hours

**Recommended Specialist:** General Physician

**When to Seek Emergency Care:**
- Fever above 103°F (39.4°C) for more than 3 days
- Difficulty breathing or chest pain
- Severe headache with stiff neck

**Follow-up Questions:**
- How many days have you had the fever?
- Are you experiencing any rash or joint pain?"""

DIABETES_RESPONSE = """**Possible Condition:** Type 2 Diabetes Management / Hyperglycaemia

**Symptoms Identified:**
- Fasting blood sugar above normal range (>126 mg/dL)
- Possible frequent urination and excessive thirst

**Common Treatments & Medicines:**
- Metformin 500mg — take with meals twice daily; standard first-line therapy for Type 2 DM
- Glipizide 5mg — if Metformin alone is insufficient; take 30 minutes before meals
- Insulin (if prescribed) — as per doctor's dosage schedule

**Recommended Precautions:**
- Avoid: white rice, maida, sugary drinks, fruit juices, potatoes
- Eat: brown rice, whole wheat roti, dal, green vegetables, protein-rich foods
- Exercise 30 minutes daily — walking is sufficient
- Check blood sugar (fasting + post-meal) weekly

**Recommended Specialist:** Endocrinologist / Diabetologist

**When to Seek Emergency Care:**
- Blood sugar above 300 mg/dL
- Symptoms of hypoglycaemia: shakiness, sweating, confusion

**Follow-up Questions:**
- Are you currently on any diabetes medication?
- What is your HbA1c level from your last test?"""

HYPERTENSION_RESPONSE = """**Possible Condition:** Hypertension (High Blood Pressure)

**Symptoms Identified:**
- Blood pressure readings consistently above 140/90 mmHg
- Possible headaches and dizziness

**Common Treatments & Medicines:**
- Amlodipine 5mg — once daily in the morning; calcium channel blocker
- Losartan 50mg — once daily; ARB class, kidney-protective
- Atenolol 50mg — once daily; beta-blocker for heart rate control

**Recommended Precautions:**
- Reduce salt intake to less than 5g per day
- DASH diet: fruits, vegetables, low-fat dairy, whole grains
- Avoid alcohol and smoking
- Exercise regularly — 30 min brisk walking, 5 days a week
- Monitor BP at home twice daily (morning and evening)

**Recommended Specialist:** Cardiologist / Internal Medicine

**When to Seek Emergency Care:**
- BP above 180/120 mmHg (hypertensive crisis)
- Chest pain, shortness of breath, or vision changes with high BP

**Follow-up Questions:**
- How long have you been experiencing high blood pressure?
- Do you have a family history of heart disease?"""

DENGUE_RESPONSE = """**Possible Condition:** Dengue Fever

**Symptoms Identified:**
- Sudden high fever (102–104°F)
- Severe headache and pain behind the eyes
- Joint and muscle pain (breakbone fever)
- Possible rash

**Common Treatments & Medicines:**
- Paracetamol 500–1000 mg every 6 hours — ONLY safe antipyretic for dengue
- ⚠️ Do NOT take Ibuprofen, Aspirin, or Diclofenac — increases bleeding risk
- ORS / coconut water — to maintain hydration and electrolytes

**Recommended Precautions:**
- Monitor platelet count daily once dengue is confirmed
- Drink minimum 3 litres of fluids daily
- Rest completely; avoid mosquito exposure
- Wear full-sleeve clothing; use mosquito nets

**Recommended Specialist:** General Physician / Infectious Disease Specialist

**When to Seek Emergency Care:**
- Platelets below 50,000
- Bleeding from gums, nose, or in urine/stool
- Severe abdominal pain or persistent vomiting

**Follow-up Questions:**
- Have you done a NS1 antigen or dengue IgM test?
- Are you in or have you recently visited a dengue-prone area?"""

HEADACHE_RESPONSE = """**Possible Condition:** Tension Headache / Migraine

**Symptoms Identified:**
- Persistent headache, possibly throbbing
- May be associated with stress, screen time, or dehydration

**Common Treatments & Medicines:**
- Paracetamol 500mg — for mild to moderate headache; repeat after 4–6 hours if needed
- Ibuprofen 400mg — for moderate pain; take with food
- Sumatriptan 50mg — specifically for migraine (only if diagnosed); take at onset
- Caffeine (tea/coffee) — can help tension headaches in small amounts

**Recommended Precautions:**
- Identify and avoid triggers: bright light, stress, irregular sleep, dehydration
- Maintain regular sleep schedule (7–8 hours)
- Stay hydrated — minimum 2.5 litres of water daily
- Limit screen time; take breaks every 30 minutes

**Recommended Specialist:** Neurologist (if headaches are frequent or severe)

**When to Seek Emergency Care:**
- Sudden worst headache of your life (thunderclap headache)
- Headache with fever, stiff neck, or confusion
- Headache after head injury

**Follow-up Questions:**
- How often do you get these headaches?
- Is the pain on one side or both sides?"""


# ── Users to create ───────────────────────────────────────────────────────────

USERS = [
    {
        "username":    "rahul_sharma",
        "email":       "rahul@example.com",
        "password":    "rahul123",
        "name":        "Rahul Sharma",
        "age":         "28",
        "blood_group": "B+",
        "conditions":  "Type 2 Diabetes, on Metformin 500mg",
        "consultations": [
            (ts(12), make_messages("I have high fever and body ache since 2 days, temperature is 102F", FEVER_RESPONSE), "MODERATE", "New Delhi"),
            (ts(8),  make_messages("My fasting blood sugar is 145 mg/dL today, what should I do?", DIABETES_RESPONSE), "MODERATE", "New Delhi"),
            (ts(3),  make_messages("I have a bad headache since morning, took paracetamol but no relief", HEADACHE_RESPONSE), "MODERATE", "New Delhi"),
        ],
        "vitals": [
            # (days_ago, systolic, diastolic, glucose, heart_rate, weight, spo2)
            (14, 122, 82, 148, 78, 72, 97),
            (12, 118, 80, 135, 76, 72, 98),
            (10, 125, 85, 152, 80, 71.5, 97),
            (8,  120, 78, 128, 75, 71.5, 98),
            (6,  117, 79, 130, 77, 71, 98),
            (4,  119, 81, 142, 78, 71, 97),
            (2,  116, 78, 125, 74, 70.5, 99),
            (0,  115, 76, 118, 73, 70.5, 98),
        ],
        "prescription": {
            "medicines": [
                {"name": "Metformin 500mg", "dose": "twice daily with meals", "duration": "ongoing",
                 "explanation": "**What it is:** Metformin is a first-line oral medication for Type 2 Diabetes.\n**How it works:** Reduces glucose production by the liver and improves insulin sensitivity.\n**Standard dosage:** 500mg twice daily with meals. Max 2000mg/day.\n**Take with food?:** Yes — reduces GI side effects.\n**Common side effects:** Nausea, diarrhoea (usually temporary), metallic taste.\n**Important warnings:** Stop before contrast CT scans; check kidney function annually.\n**Tip:** Take at the same time each day and never skip doses even if you feel well."},
                {"name": "Dolo 650 (Paracetamol)", "dose": "as needed for fever/pain", "duration": "5 days",
                 "explanation": "**What it is:** Analgesic and antipyretic for pain and fever relief.\n**How it works:** Blocks pain signals and reduces fever by acting on the hypothalamus.\n**Standard dosage:** 500–1000mg every 6–8 hours. Max 4g/day.\n**Take with food?:** Not required, but food reduces stomach upset.\n**Common side effects:** Rarely causes side effects at normal doses.\n**Important warnings:** Do not exceed 4g/day; avoid alcohol; caution in liver disease.\n**Tip:** Do not take other cold/flu medicines simultaneously as they may also contain paracetamol."},
            ]
        },
    },
    {
        "username":    "priya_patel",
        "email":       "priya@example.com",
        "password":    "priya123",
        "name":        "Priya Patel",
        "age":         "35",
        "blood_group": "A+",
        "conditions":  "Hypertension, on Amlodipine 5mg",
        "consultations": [
            (ts(20), make_messages("My blood pressure is 155/95 consistently for 3 days, I'm on Amlodipine", HYPERTENSION_RESPONSE), "MODERATE", "Mumbai"),
            (ts(10), make_messages("I had high fever 103F and severe joint pain, could it be dengue?", DENGUE_RESPONSE), "SEVERE", "Mumbai"),
            (ts(2),  make_messages("Mild headache for 2 days, no fever, possibly from stress at work", HEADACHE_RESPONSE), "MILD", "Mumbai"),
        ],
        "vitals": [
            (14, 158, 96, 95,  82, 65, 97),
            (12, 152, 92, 92,  80, 65, 97),
            (10, 148, 90, 98,  79, 64.5, 98),
            (8,  145, 88, 94,  78, 64.5, 98),
            (6,  140, 86, 90,  77, 64, 99),
            (4,  138, 85, 92,  76, 64, 98),
            (2,  135, 84, 89,  75, 63.5, 99),
            (0,  132, 82, 88,  74, 63.5, 98),
        ],
        "prescription": {
            "medicines": [
                {"name": "Amlodipine 5mg", "dose": "once daily morning", "duration": "ongoing",
                 "explanation": "**What it is:** Calcium channel blocker for high blood pressure and chest pain.\n**How it works:** Relaxes blood vessel walls, reducing the heart's workload.\n**Standard dosage:** 5mg once daily in the morning. Can be increased to 10mg.\n**Take with food?:** Doesn't matter — take consistently at same time.\n**Common side effects:** Ankle swelling, flushing, dizziness (especially when standing up).\n**Important warnings:** Don't stop suddenly; grapefruit juice can increase drug levels.\n**Tip:** Check BP daily at the same time each morning before taking the tablet."},
            ]
        },
    },
    {
        "username":    "demo",
        "email":       "demo@mediassist.ai",
        "password":    "demo123",
        "name":        "Demo User",
        "age":         "30",
        "blood_group": "O+",
        "conditions":  "",
        "consultations": [
            (ts(5), make_messages("I have a sore throat, mild fever 99F, and runny nose since yesterday", FEVER_RESPONSE), "MILD", "Bengaluru"),
            (ts(2), make_messages("What medicines should I take for a tension headache?", HEADACHE_RESPONSE), "MILD", "Bengaluru"),
        ],
        "vitals": [
            (7, 118, 76, 88, 72, 68, 99),
            (5, 116, 74, 85, 70, 68, 99),
            (3, 119, 77, 90, 71, 67.5, 98),
            (1, 115, 75, 86, 69, 67.5, 99),
        ],
        "prescription": None,
    },
]


# ── Seed ─────────────────────────────────────────────────────────────────────

created = 0
skipped = 0

for u in USERS:
    if get_user(u["username"]):
        print(f"  [skip] {u['username']} already exists")
        skipped += 1
        continue

    # Create user
    user = create_user(
        username=u["username"], email=u["email"],
        password_hash=hash_password(u["password"]),
        name=u["name"], age=u["age"],
        blood_group=u["blood_group"], conditions=u["conditions"],
    )
    uid = user["id"]
    print(f"  [OK] Created user: {u['username']} (password: {u['password']})")

    # Consultations
    for i, (timestamp, messages, severity, city) in enumerate(u["consultations"]):
        session_id = f"{uid[:8]}_sess_{i+1}"
        save_consultation(uid, session_id, messages, severity, city)

    print(f"       {len(u['consultations'])} consultations saved")

    # Vitals
    for days_ago, sys_bp, dia_bp, glucose, hr, weight, spo2 in u["vitals"]:
        # We need to write with specific timestamps — use SQLite directly for seeding
        record_ts = ts(days_ago, hour=8)
        readings = {
            "systolic_bp": sys_bp, "diastolic_bp": dia_bp,
            "glucose": glucose, "heart_rate": hr,
            "weight": weight, "spo2": spo2,
        }

        if is_cloud():
            from src.database import _sb
            record = {"id": _uid(), "user_id": uid, "timestamp": record_ts}
            record.update(readings)
            try:
                _sb.table("vitals").insert(record).execute()
            except Exception as e:
                print(f"       [warn] vitals cloud insert failed: {e}")
                save_vital(uid, readings)
        else:
            from src.database import _SQLITE_PATH
            cols = ["id", "user_id", "timestamp"] + list(readings.keys())
            vals = [_uid(), uid, record_ts] + list(readings.values())
            with _conn() as c:
                c.execute(
                    f"INSERT INTO vitals ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                    vals
                )
                c.commit()

    print(f"       {len(u['vitals'])} vitals readings saved")

    # Prescriptions
    if u["prescription"]:
        save_prescription(uid, u["prescription"]["medicines"])
        print(f"       1 prescription saved")

    created += 1
    print()

print(f"Seeding complete: {created} users created, {skipped} already existed.")
print()
print("Login credentials:")
print("  Username: rahul_sharma   Password: rahul123  (Diabetic patient, 8 vitals readings)")
print("  Username: priya_patel    Password: priya123  (Hypertension patient, 8 vitals readings)")
print("  Username: demo           Password: demo123   (Clean demo account)")
