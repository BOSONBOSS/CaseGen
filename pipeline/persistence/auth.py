"""User authentication and credential management for CaseGen.

Uses local SQLite persistence (shared case_history.db) and NIST-recommended
PBKDF2-HMAC-SHA256 password hashing with unique per-user cryptographic salts.
Built strictly with Python's standard library — zero external dependencies.
"""

import hashlib
import hmac
import html
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
    """Initializes the users table, migrates legacy schema if needed, and seeds accounts."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate legacy student_id column to email if an older table exists
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "student_id" in cols and "email" not in cols:
            conn.execute("ALTER TABLE users RENAME COLUMN student_id TO email")
        conn.commit()

    # Pre-seed the 4 team member accounts
    demo_accounts = [
        ("ananshi", "CaseGen@2026", "Ananshi Sharma", "ananshi@casegen.edu"),
        ("aditya", "CaseGen@2026", "Aditya Nadar", "aditya@casegen.edu"),
        ("sumit", "CaseGen@2026", "Sumit Singh", "sumit@casegen.edu"),
        ("dhruv", "CaseGen@2026", "Dhruv Sharma", "dhruv@casegen.edu"),
    ]

    for uname, pwd, name, email in demo_accounts:
        _seed_account_if_missing(uname, pwd, name, email)


def _seed_account_if_missing(
    username: str, password: str, full_name: str, email: str
) -> None:
    """Inserts a user if missing, or upgrades legacy non-email placeholder on seeded accounts."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, email FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None:
            pwd_hash, salt = _hash_password(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, full_name, email) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, pwd_hash, salt, full_name, email),
            )
            conn.commit()
        elif "@" not in (row["email"] or ""):
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (email, row["id"]),
            )
            conn.commit()


def register_user(
    username: str, password: str, full_name: str, email: str
) -> Union[bool, str]:
    """Registers a new user account.

    Returns:
        True on success, or a human-readable error message string on failure.
    """
    u = (username or "").strip()
    p = (password or "").strip()
    fn = (full_name or "").strip()
    em = (email or "").strip()

    if not u or not p or not fn or not em:
        return "All fields are required."

    if "@" not in em or "." not in em.split("@")[-1] or em.startswith("@"):
        return "Please enter a valid email address."

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
                "INSERT INTO users (username, password_hash, salt, full_name, email) "
                "VALUES (?, ?, ?, ?, ?)",
                (u, pwd_hash, salt, fn, em),
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
            "SELECT username, full_name, email FROM users WHERE username = ?",
            (u,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "username": row["username"],
        "full_name": row["full_name"],
        "email": row["email"],
    }


def render_sidebar_auth(on_home: bool = False) -> None:
    """Renders the 'Signed in as' badge and 'Log out' button in the sidebar."""
    import streamlit as st

    if not st.session_state.get("authenticated", False):
        return

    user_info = st.session_state.get("user_info") or {}
    raw_name = user_info.get("full_name") or st.session_state.get("username", "User")
    raw_email = user_info.get("email", "")
    display_name = html.escape(raw_name)
    email_html = (
        f"<div style='font-size:11px; color:#64748B; margin-top:2px; "
        f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>"
        f"{html.escape(raw_email)}</div>"
        if raw_email
        else ""
    )

    st.sidebar.markdown(
        f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:0.6rem 0.8rem; margin:0.25rem 0 0.5rem;">
            <div style="font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:#64748B;">Signed in as</div>
            <div style="font-size:13px; font-weight:600; color:#0F172A; margin-top:2px;">{display_name}</div>
            {email_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Log out", key="sidebar_logout_btn", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["user_info"] = None
        st.session_state["show_auth"] = False
        if on_home:
            st.rerun()
        else:
            st.switch_page("Home.py")
    st.sidebar.divider()


def require_auth() -> None:
    """Route guard for protected workspace pages (Pages 1–6).

    Redirects unauthenticated visitors straight to the Sign In screen on Home.py,
    and renders the consistent 'Signed in as' + 'Log out' sidebar section when signed in.
    """
    import streamlit as st

    if not st.session_state.get("authenticated", False):
        st.session_state["show_auth"] = True
        st.switch_page("Home.py")

    render_sidebar_auth(on_home=False)
