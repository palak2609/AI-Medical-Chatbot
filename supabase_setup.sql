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
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

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
ALTER TABLE consultations ENABLE ROW LEVEL SECURITY;

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
ALTER TABLE vitals ENABLE ROW LEVEL SECURITY;

-- Prescriptions (decoded prescriptions per user)
CREATE TABLE IF NOT EXISTS prescriptions (
    id        TEXT PRIMARY KEY,
    user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TEXT,
    medicines JSONB
);
ALTER TABLE prescriptions ENABLE ROW LEVEL SECURITY;

-- Indexes for fast per-user lookups
CREATE INDEX IF NOT EXISTS idx_consultations_user ON consultations(user_id);
CREATE INDEX IF NOT EXISTS idx_vitals_user        ON vitals(user_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_user ON prescriptions(user_id);

-- ═══════════════════════════════════════════════════════════════════
-- NOTE: We use the service_role key in our Python backend.
-- service_role bypasses RLS entirely — no policies needed.
-- Tables are safe: anon/public cannot access them without policies.
-- ═══════════════════════════════════════════════════════════════════
