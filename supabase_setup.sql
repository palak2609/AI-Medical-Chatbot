-- ═══════════════════════════════════════════════════════════════════
-- AI Medical Assistant — Supabase PostgreSQL Schema
-- Run this entire file in the Supabase SQL Editor
-- (supabase.com → your project → SQL Editor → New query → Paste → Run)
-- ═══════════════════════════════════════════════════════════════════

-- Users
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

-- Consultations (full chat sessions per user)
CREATE TABLE IF NOT EXISTS consultations (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT,
    messages   JSONB,
    severity   TEXT DEFAULT 'MILD',
    city       TEXT DEFAULT '',
    timestamp  TEXT
);

-- Vitals (health readings per user)
CREATE TABLE IF NOT EXISTS vitals (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp    TEXT,
    systolic_bp  REAL,
    diastolic_bp REAL,
    glucose      REAL,
    heart_rate   REAL,
    weight       REAL,
    spo2         REAL
);

-- Prescriptions (decoded prescriptions per user)
CREATE TABLE IF NOT EXISTS prescriptions (
    id        TEXT PRIMARY KEY,
    user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TEXT,
    medicines JSONB
);

-- Indexes for fast per-user lookups
CREATE INDEX IF NOT EXISTS idx_consultations_user ON consultations(user_id);
CREATE INDEX IF NOT EXISTS idx_vitals_user        ON vitals(user_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_user ON prescriptions(user_id);
