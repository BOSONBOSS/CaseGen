"""SQLite history for generated case studies."""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional


DB_PATH = "case_history.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                theme TEXT,
                created_at TEXT NOT NULL,
                markdown_path TEXT NOT NULL
            )
        """)
        conn.commit()


def save_case(company_name: str, theme: str, markdown_path: str) -> int:
    init_db()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO cases (company_name, theme, created_at, markdown_path) VALUES (?, ?, ?, ?)",
            (company_name, theme, datetime.now().isoformat(), markdown_path),
        )
        conn.commit()
        return cur.lastrowid


def list_cases(limit: int = 50) -> List[dict]:
    init_db()
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, company_name, theme, created_at, markdown_path FROM cases ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_case(case_id: int) -> Optional[dict]:
    init_db()
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, company_name, theme, created_at, markdown_path FROM cases WHERE id = ?",
            (case_id,),
        ).fetchone()
    return dict(row) if row else None
