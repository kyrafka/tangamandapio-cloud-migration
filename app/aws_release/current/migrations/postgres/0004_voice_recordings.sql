-- 0004_voice_recordings: consentimiento explícito y metadatos de grabación.
-- El audio vive en un directorio privado, nunca dentro de static ni en la BD.
ALTER TABLE voice_signals DROP CONSTRAINT IF EXISTS voice_signals_kind_check;
ALTER TABLE voice_signals ADD CONSTRAINT voice_signals_kind_check
    CHECK (kind IN ('offer','answer','ice','hangup','reject','recording_request','recording_approved','recording_declined','recording_stopped'));
CREATE TABLE IF NOT EXISTS voice_recordings (
    call_id TEXT PRIMARY KEY REFERENCES voice_calls(id),
    caller_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    callee_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    requester_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    status TEXT NOT NULL CHECK (status IN ('requested','approved','declined','stopped','saved')),
    caller_consented BOOLEAN NOT NULL DEFAULT FALSE,
    callee_consented BOOLEAN NOT NULL DEFAULT FALSE,
    storage_name TEXT UNIQUE,
    mime_type TEXT,
    size_bytes BIGINT,
    sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    uploaded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_voice_recordings_participants
    ON voice_recordings(caller_user_id, callee_user_id, status, created_at);
