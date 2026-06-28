"""Save and restore session artifacts to survive browser refresh."""

import json
import os
from datetime import datetime
from glob import glob
from typing import Optional


OUTPUT_DIR = "output"


def _ensure_output():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_fact_sheet(fact_sheet) -> str:
    _ensure_output()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"fact_sheet_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fact_sheet.model_dump_json(indent=2))
    return path


def save_case_markdown(markdown: str, company_name: str = "case") -> str:
    _ensure_output()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in company_name)[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"case_{safe}_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return path


def get_latest_fact_sheet_path() -> Optional[str]:
    _ensure_output()
    files = sorted(glob(os.path.join(OUTPUT_DIR, "fact_sheet_*.json")), reverse=True)
    return files[0] if files else None


def get_latest_case_path() -> Optional[str]:
    _ensure_output()
    files = sorted(glob(os.path.join(OUTPUT_DIR, "case_*.md")), reverse=True)
    return files[0] if files else None


def load_fact_sheet(path: str):
    from pipeline.models.schemas import FactSheet
    with open(path, encoding="utf-8") as f:
        return FactSheet(**json.load(f))


def load_case_markdown(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
