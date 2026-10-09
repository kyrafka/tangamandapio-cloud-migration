-- 0002_login_attempts: contador de intentos de login compartido por todas las
-- instancias. El limite vivia en un mapa por proceso, asi que con dos
-- instancias y dos workers el umbral efectivo se multiplicaba por cuatro.
CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_key TEXT PRIMARY KEY,
    failures INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0
);
