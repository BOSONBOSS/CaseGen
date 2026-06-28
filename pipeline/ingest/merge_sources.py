"""Helpers for dict-based master transcript merge and backup."""

import json
import os
from datetime import datetime
from typing import Optional


def merge_to_text(master_transcript: dict) -> str:
    """Combine source-keyed transcript dict into a single string for chunking."""
    if not master_transcript:
        return ""
    if isinstance(master_transcript, str):
        return master_transcript

    parts = []
    for filename, text in master_transcript.items():
        if text and str(text).strip():
            parts.append(f"\n\n[Source: {filename}]\n{text}")
    return "".join(parts)


def total_char_count(master_transcript: dict) -> int:
    """Return total character count across all sources."""
    if isinstance(master_transcript, str):
        return len(master_transcript)
    return sum(len(str(v)) for v in (master_transcript or {}).values())


def save_backup(master_transcript: dict, warnings: Optional[list] = None) -> str:
    """Persist master transcript dict as JSON. Returns path written."""
    os.makedirs("session_backup", exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(),
        "sources": master_transcript,
        "warnings": warnings or [],
    }
    path = "session_backup/master_transcript.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def detect_homepage_junk(text: str) -> Optional[str]:
    """
    Heuristic: homepage scrapes have many short lines and nav-like keywords.
    Returns warning message if junk detected, else None.
    """
    if not text or len(text) < 200:
        return None

    lower = text.lower()
    nav_keywords = ["cookie", "privacy policy", "sign in", "subscribe", "menu", "navigation"]
    nav_hits = sum(1 for kw in nav_keywords if kw in lower)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln) < 40)
    short_ratio = short_lines / max(len(lines), 1)

    if nav_hits >= 3 and short_ratio > 0.5:
        return (
            "This content looks like a website homepage (navigation menus, cookie banners) "
            "rather than a report or article. Upload a PDF annual report or link directly to a PDF/article."
        )
    return None
