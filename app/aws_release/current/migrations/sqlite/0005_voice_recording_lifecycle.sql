-- 0005_voice_recording_lifecycle: sincroniza el inicio y endurece el ciclo de vida.
DROP INDEX IF EXISTS idx_voice_signals_recipient;
ALTER TABLE voice_signals RENAME TO voice_signals_v4;
CREATE TABLE voice_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT NOT NULL,
    sender_user_id INTEGER NOT NULL,
    recipient_user_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('offer','answer','ice','hangup','reject','recording_request','recording_approved','recording_declined','recording_started','recording_stopped')),
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivered_at TEXT,
    FOREIGN KEY(call_id) REFERENCES voice_calls(id),
    FOREIGN KEY(sender_user_id) REFERENCES portal_users(id),
    FOREIGN KEY(recipient_user_id) REFERENCES portal_users(id)
);
INSERT INTO voice_signals(id, call_id, sender_user_id, recipient_user_id, kind, payload, created_at, delivered_at)
SELECT id, call_id, sender_user_id, recipient_user_id, kind, payload, created_at, delivered_at
FROM voice_signals_v4;
DROP TABLE voice_signals_v4;
CREATE INDEX idx_voice_signals_recipient
    ON voice_signals(recipient_user_id, call_id, delivered_at, id);

DROP INDEX IF EXISTS idx_voice_recordings_participants;
ALTER TABLE voice_recordings RENAME TO voice_recordings_v4;
CREATE TABLE voice_recordings (
    call_id TEXT PRIMARY KEY,
    caller_user_id INTEGER NOT NULL,
    callee_user_id INTEGER NOT NULL,
    requester_user_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('requested','approved','recording','declined','stopped','saved')),
    caller_consented INTEGER NOT NULL DEFAULT 0,
    callee_consented INTEGER NOT NULL DEFAULT 0,
    storage_name TEXT UNIQUE,
    mime_type TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    uploaded_at TEXT,
    expires_at TEXT NOT NULL,
    FOREIGN KEY(call_id) REFERENCES voice_calls(id),
    FOREIGN KEY(caller_user_id) REFERENCES portal_users(id),
    FOREIGN KEY(callee_user_id) REFERENCES portal_users(id),
    FOREIGN KEY(requester_user_id) REFERENCES portal_users(id)
);
INSERT INTO voice_recordings(
    call_id, caller_user_id, callee_user_id, requester_user_id, status,
    caller_consented, callee_consented, storage_name, mime_type, size_bytes,
    sha256, created_at, updated_at, uploaded_at, expires_at
)
SELECT
    call_id, caller_user_id, callee_user_id, requester_user_id, status,
    caller_consented, callee_consented, storage_name, mime_type, size_bytes,
    sha256, created_at, updated_at, uploaded_at, expires_at
FROM voice_recordings_v4;
DROP TABLE voice_recordings_v4;
CREATE INDEX idx_voice_recordings_participants
    ON voice_recordings(caller_user_id, callee_user_id, status, created_at);
