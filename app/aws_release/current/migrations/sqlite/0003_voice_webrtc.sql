-- 0003_voice_webrtc: señalización persistente para llamadas internas WebRTC.
-- No almacena audio, credenciales SIP ni grabaciones; solamente los mensajes
-- efímeros de señalización necesarios para establecer una llamada interna.
CREATE TABLE IF NOT EXISTS voice_calls (
    id TEXT PRIMARY KEY,
    caller_user_id INTEGER NOT NULL,
    callee_user_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ringing','accepted','rejected','ended','cancelled','expired')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY(caller_user_id) REFERENCES portal_users(id),
    FOREIGN KEY(callee_user_id) REFERENCES portal_users(id)
);
CREATE INDEX IF NOT EXISTS idx_voice_calls_participants
    ON voice_calls(caller_user_id, callee_user_id, updated_at);
CREATE TABLE IF NOT EXISTS voice_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT NOT NULL,
    sender_user_id INTEGER NOT NULL,
    recipient_user_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('offer','answer','ice','hangup','reject')),
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivered_at TEXT,
    FOREIGN KEY(call_id) REFERENCES voice_calls(id),
    FOREIGN KEY(sender_user_id) REFERENCES portal_users(id),
    FOREIGN KEY(recipient_user_id) REFERENCES portal_users(id)
);
CREATE INDEX IF NOT EXISTS idx_voice_signals_recipient
    ON voice_signals(recipient_user_id, call_id, delivered_at, id);
