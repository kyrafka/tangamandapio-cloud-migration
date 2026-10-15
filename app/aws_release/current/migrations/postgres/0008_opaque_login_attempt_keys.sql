-- Recreate ephemeral login counters without IP/user identifiers in clear text.
-- The values are temporary security state, so clearing them once avoids
-- preserving the legacy raw keys while the application switches to HMAC keys.
DELETE FROM login_attempts;
