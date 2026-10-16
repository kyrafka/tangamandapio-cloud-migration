CREATE INDEX IF NOT EXISTS idx_outbox_created_event_id
ON outbox_events (created_at DESC, event_id DESC);
