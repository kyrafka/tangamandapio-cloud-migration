-- 0003_voice_webrtc: señalización persistente para llamadas internas WebRTC.
-- No almacena audio, credenciales SIP ni grabaciones; solamente los mensajes
-- efímeros de señalización necesarios para establecer una llamada interna.
CREATE TABLE IF NOT EXISTS voice_calls (
    id TEXT PRIMARY KEY,
    caller_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    callee_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    status TEXT NOT NULL CHECK (status IN ('ringing','accepted','rejected','ended','cancelled','expired')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voice_calls_participants
    ON voice_calls(caller_user_id, callee_user_id, updated_at);
CREATE TABLE IF NOT EXISTS voice_signals (
    id BIGSERIAL PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES voice_calls(id),
    sender_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    recipient_user_id BIGINT NOT NULL REFERENCES portal_users(id),
    kind TEXT NOT NULL CHECK (kind IN ('offer','answer','ice','hangup','reject')),
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voice_signals_recipient
    ON voice_signals(recipient_user_id, call_id, delivered_at, id);
