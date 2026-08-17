import json
import sqlite3
from datetime import datetime, timezone
from src.utils.config import DB_FILE

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def connect():
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT UNIQUE NOT NULL,
            identifier_type TEXT NOT NULL,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            otp_hash TEXT NOT NULL,
            otp_salt TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        conn.commit()
    finally:
        conn.close()

def get_user(identifier):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE identifier=?",
            (identifier,)
        ).fetchone()
    finally:
        conn.close()

def create_user(identifier, identifier_type, display_name, password_hash, password_salt):
    conn = connect()
    try:
        now = now_iso()
        conn.execute("""
        INSERT INTO users
        (identifier, identifier_type, display_name, password_hash,
         password_salt, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            identifier, identifier_type, display_name,
            password_hash, password_salt, now, now
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_password(user_id, password_hash, password_salt):
    conn = connect()
    try:
        conn.execute("""
        UPDATE users
        SET password_hash=?, password_salt=?, updated_at=?
        WHERE id=?
        """, (password_hash, password_salt, now_iso(), user_id))
        conn.commit()
    finally:
        conn.close()

def save_otp(user_id, otp_hash, otp_salt, expires_at):
    conn = connect()
    try:
        conn.execute(
            "UPDATE password_reset_otps SET used=1 WHERE user_id=? AND used=0",
            (user_id,)
        )
        conn.execute("""
        INSERT INTO password_reset_otps
        (user_id, otp_hash, otp_salt, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, otp_hash, otp_salt, expires_at, now_iso()))
        conn.commit()
    finally:
        conn.close()

def get_active_otp(user_id):
    conn = connect()
    try:
        return conn.execute("""
        SELECT * FROM password_reset_otps
        WHERE user_id=? AND used=0
        ORDER BY id DESC LIMIT 1
        """, (user_id,)).fetchone()
    finally:
        conn.close()

def increment_otp_attempt(row_id):
    conn = connect()
    try:
        conn.execute(
            "UPDATE password_reset_otps SET attempts=attempts+1 WHERE id=?",
            (row_id,)
        )
        conn.commit()
    finally:
        conn.close()

def consume_otp(row_id):
    conn = connect()
    try:
        conn.execute(
            "UPDATE password_reset_otps SET used=1 WHERE id=?",
            (row_id,)
        )
        conn.commit()
    finally:
        conn.close()

def save_chat(user_id, question, answer, sources):
    conn = connect()
    try:
        conn.execute("""
        INSERT INTO chat_history
        (user_id, question, answer, sources_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            user_id, question, answer,
            json.dumps(sources, ensure_ascii=False),
            now_iso()
        ))
        conn.commit()
    finally:
        conn.close()

def recent_chats(user_id, limit=20):
    conn = connect()
    try:
        rows = conn.execute("""
        SELECT question, answer, sources_json, created_at
        FROM chat_history
        WHERE user_id=?
        ORDER BY id DESC LIMIT ?
        """, (user_id, limit)).fetchall()
        return list(reversed(rows))
    finally:
        conn.close()
