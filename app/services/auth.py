"""Sadə autentifikasiya: istifadəçilər (sərnişin / operator), PBKDF2 şifrə heşi, cookie sessiyaları."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from ..db import Database, to_iso, utcnow

ROLES = ("passenger", "operator")
SESSION_COOKIE = "st_session"
AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""
DEMO_USERS = [  # münsiflər üçün hazır hesablar (login səhifəsində göstərilir)
    ("operator", "operator123", "operator", "Dispetçer (demo)"),
    ("sernisin", "sernisin123", "passenger", "Sərnişin (demo)"),
]


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored) and bool(digest)


class AuthService:
    def __init__(self, db: Database) -> None:
        self.db = db
        with db.transaction() as conn:
            conn.executescript(AUTH_SCHEMA)
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "email" not in cols:  # köhnə baza üçün miqrasiya
                conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        for username, pw, role, name in DEMO_USERS:
            if self.db.query_one("SELECT id FROM users WHERE username=?", (username,)) is None:
                self.register(username, pw, role, name)

    def register(self, username: str, password: str, role: str, full_name: str | None = None, email: str | None = None) -> dict:
        username = username.strip().lower()
        if role not in ROLES:
            raise ValueError("role")
        if len(username) < 3 or len(password) < 6:
            raise ValueError("short")
        if self.db.query_one("SELECT id FROM users WHERE username=?", (username,)):
            raise ValueError("exists")
        if email and self.db.query_one("SELECT id FROM users WHERE email=?", (email.strip().lower(),)):
            raise ValueError("email_exists")
        cur = self.db.execute(
            "INSERT INTO users(username, password_hash, role, full_name, email, created_at) VALUES (?,?,?,?,?,?)",
            (username, hash_password(password), role, (full_name or "").strip() or None,
             (email or "").strip().lower() or None, to_iso(utcnow())),
        )
        return self.public_user(self.db.query_one("SELECT * FROM users WHERE id=?", (cur.lastrowid,)))

    def authenticate(self, username: str, password: str) -> dict | None:
        key = username.strip().lower()
        row = self.db.query_one("SELECT * FROM users WHERE username=? OR email=?", (key, key))
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        return self.public_user(row)

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)", (token, user_id, to_iso(utcnow())))
        return token

    def user_by_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        row = self.db.query_one(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?", (token,))
        return self.public_user(row) if row else None

    def delete_session(self, token: str | None) -> None:
        if token:
            self.db.execute("DELETE FROM sessions WHERE token=?", (token,))

    @staticmethod
    def public_user(row: dict) -> dict:
        return {"id": row["id"], "username": row["username"], "role": row["role"], "full_name": row["full_name"],
                "email": row.get("email") if isinstance(row, dict) else None}
