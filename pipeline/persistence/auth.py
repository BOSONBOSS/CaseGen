"""User authentication and credential management for CaseGen.

Uses local SQLite persistence (shared case_history.db) and NIST-recommended
PBKDF2-HMAC-SHA256 password hashing with unique per-user cryptographic salts.
Built strictly with Python's standard library — zero external dependencies.
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
from typing import Dict, Optional, Tuple, Union

# Locate database at project root reliably regardless of current working directory
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_BASE_DIR, "case_history.db")
PBKDF2_ITERATIONS = 100_000


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes a password with PBKDF2-HMAC-SHA256 and a random salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return key.hex(), salt


def init_users_table() -> None:
    """Initializes the users table and seeds demo accounts if they do not exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                student_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    # Pre-seed the 4 student team member accounts for course evaluation
    demo_accounts = [
        ("ananshi", "CaseGen@2026", "Ananshi Sharma", "240377"),
        ("aditya", "CaseGen@2026", "Aditya Nadar", "240368"),
        ("sumit", "CaseGen@2026", "Sumit Singh", "240344"),
        ("dhruv", "CaseGen@2026", "Dhruv Sharma", "240444"),
    ]

    for uname, pwd, name, sid in demo_accounts:
        _seed_account_if_missing(uname, pwd, name, sid)


def _seed_account_if_missing(
    username: str, password: str, full_name: str, student_id: str
) -> None:
    """Inserts a user only if the username is not already present."""
    with _get_connection() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone() is None:
            pwd_hash, salt = _hash_password(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, full_name, student_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, pwd_hash, salt, full_name, student_id),
            )
            conn.commit()


def register_user(
    username: str, password: str, full_name: str, student_id: str
) -> Union[bool, str]:
    """Registers a new user account.

    Returns:
        True on success, or a human-readable error message string on failure.
    """
    u = (username or "").strip()
    p = (password or "").strip()
    fn = (full_name or "").strip()
    sid = (student_id or "").strip()

    if not u or not p or not fn or not sid:
        return "All fields are required."

    if len(u) < 3:
        return "Username must be at least 3 characters long."

    if len(p) < 6:
        return "Password must be at least 6 characters long."

    init_users_table()

    try:
        with _get_connection() as conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (u,))
            if cursor.fetchone() is not None:
                return f"Username '{u}' is already taken. Please choose another."

            pwd_hash, salt = _hash_password(p)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, full_name, student_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (u, pwd_hash, salt, fn, sid),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return f"Username '{u}' is already taken."
    except Exception as e:
        return f"Registration failed: {str(e)}"


def verify_login(username: str, password: str) -> bool:
    """Verifies username and password against SQLite using constant-time comparison.

    Returns:
        True if credentials are valid, False otherwise.
    """
    u = (username or "").strip()
    p = password or ""

    if not u or not p:
        return False

    init_users_table()

    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            (u,),
        )
        row = cursor.fetchone()

    if row is None:
        # Perform dummy hash to prevent timing side-channel attacks
        _hash_password("dummy_password", secrets.token_hex(16))
        return False

    stored_hash = row["password_hash"]
    salt = row["salt"]
    computed_hash, _ = _hash_password(p, salt)

    return hmac.compare_digest(stored_hash, computed_hash)


def get_user_info(username: str) -> Optional[Dict[str, str]]:
    """Fetches non-sensitive profile metadata for an authenticated user."""
    u = (username or "").strip()
    if not u:
        return None

    init_users_table()

    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT username, full_name, student_id FROM users WHERE username = ?",
            (u,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "username": row["username"],
        "full_name": row["full_name"],
        "student_id": row["student_id"],
    }


def require_auth() -> None:
    """Route guard for protected workspace pages (Pages 1–6).

    Redirects unauthenticated visitors straight to the Sign In screen on Home.py.
    """
    import streamlit as st

    if not st.session_state.get("authenticated", False):
        st.session_state["show_auth"] = True
        st.switch_page("Home.py")
