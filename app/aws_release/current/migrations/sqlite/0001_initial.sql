-- 0001_initial: esquema base del portal B2B en SQLite (pruebas locales).
-- Cada sentencia termina en punto y coma y el runner la ejecuta por separado.
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS portal_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('customer','sales','warehouse','operations','admin','auditor')),
    company_id INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES portal_users(id)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    total REAL NOT NULL CHECK (total >= 0),
    created_at TEXT NOT NULL,
    company_id INTEGER,
    created_by INTEGER,
    reference TEXT,
    status TEXT NOT NULL DEFAULT 'created'
);
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id TEXT PRIMARY KEY,
    order_id INTEGER NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    delivered_at TEXT
);
