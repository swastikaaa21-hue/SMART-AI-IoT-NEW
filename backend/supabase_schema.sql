-- ============================================================
--  SMART AI IoT - Supabase Database Schema
--  Run this SQL in Supabase SQL Editor to create all tables
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name   TEXT,
    is_active   BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── Rooms ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rooms (
    id          TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    room_type   TEXT NOT NULL,
    description TEXT,
    icon        TEXT,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rooms_owner ON rooms(owner_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rooms_slug_owner ON rooms(slug, owner_id);

-- ── Devices ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS devices (
    id              TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    device_id       TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    device_type     TEXT NOT NULL,
    room_id         TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    state           TEXT DEFAULT 'off' NOT NULL,
    brightness      INTEGER,
    temperature     DOUBLE PRECISION,
    humidity        DOUBLE PRECISION,
    target_temperature INTEGER,
    ac_mode         TEXT,
    fan_speed       INTEGER,
    timer_minutes   INTEGER,
    extra_metadata  JSONB DEFAULT '{}'::jsonb,
    is_online       BOOLEAN DEFAULT FALSE NOT NULL,
    firmware_version TEXT,
    description     TEXT,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_room ON devices(room_id);

-- ── Telemetry Logs ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id          TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    device_id   TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION,
    power_watts DOUBLE PRECISION,
    extra_data  JSONB,
    recorded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_recorded ON telemetry_logs(recorded_at DESC);

-- ── Command Logs ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS command_logs (
    id            TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    device_id     TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    action        TEXT NOT NULL,
    payload       JSONB,
    source        TEXT DEFAULT 'api' NOT NULL,
    status        TEXT DEFAULT 'sent' NOT NULL,
    error_message TEXT,
    executed_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_commands_device ON command_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_commands_executed ON command_logs(executed_at DESC);

-- ── Chat Sessions ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT DEFAULT 'New Chat' NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);

-- ── Chat Messages ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id                TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    session_id        TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role              TEXT NOT NULL,
    content           TEXT NOT NULL,
    function_call     TEXT,
    function_response TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);

-- ── Schedules ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id          TEXT PRIMARY KEY DEFAULT replace(uuid_generate_v4()::text, '-', ''),
    name        TEXT NOT NULL,
    room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    device_id   TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    action      TEXT NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT,
    is_active   BOOLEAN DEFAULT TRUE NOT NULL,
    days        TEXT DEFAULT '1,2,3,4,5,6,7' NOT NULL,
    parameters  TEXT,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schedules_user ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_device ON schedules(device_id);

-- ── Row Level Security (RLS) ────────────────────────────────
-- Disable RLS for service-key access (backend uses service key)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE rooms DISABLE ROW LEVEL SECURITY;
ALTER TABLE devices DISABLE ROW LEVEL SECURITY;
ALTER TABLE telemetry_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE command_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE schedules DISABLE ROW LEVEL SECURITY;
