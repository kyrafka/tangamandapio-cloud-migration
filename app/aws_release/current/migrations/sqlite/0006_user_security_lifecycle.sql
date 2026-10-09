-- 0006_user_security_lifecycle: invalidate stale sessions and require change
-- after an administrator issues a temporary password.
ALTER TABLE portal_users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE portal_users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0;
