-- 0005_voice_recording_lifecycle: sincroniza el inicio y endurece el ciclo de vida.
ALTER TABLE voice_signals DROP CONSTRAINT IF EXISTS voice_signals_kind_check;
ALTER TABLE voice_signals ADD CONSTRAINT voice_signals_kind_check
    CHECK (kind IN ('offer','answer','ice','hangup','reject','recording_request','recording_approved','recording_declined','recording_started','recording_stopped'));
ALTER TABLE voice_recordings DROP CONSTRAINT IF EXISTS voice_recordings_status_check;
ALTER TABLE voice_recordings ADD CONSTRAINT voice_recordings_status_check
    CHECK (status IN ('requested','approved','recording','declined','stopped','saved'));
