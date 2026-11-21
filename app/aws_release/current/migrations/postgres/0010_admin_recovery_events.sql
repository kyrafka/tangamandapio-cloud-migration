CREATE TABLE IF NOT EXISTS portal_admin_recovery_events (
    secret_version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
