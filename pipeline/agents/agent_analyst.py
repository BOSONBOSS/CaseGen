"""Agent 3 — Analyst: exhibits (Markdown tables) and discussion questions."""

import json

from pipeline.agents.llm_client import generate_json
from config import EXHIBITS_CONFIG

_ANALYST_PROMPT = """
You are a case study analyst. Generate exhibits and discussion questions from the FactSheet ONLY.

Rules:
- exhibits: Markdown tables (financial comparison, timeline, KPI before/after). Skip if no numeric data.
- discussion_questions: {num_questions} open-ended questions for {audience_level} audience.
- Do NOT invent numbers. Use ONLY data from the FactSheet.
- If FactSheet lacks numeric data, set exhibits to an empty string.

Return ONLY valid JSON:
{{
  "exhibits": "## Exhibits\\n\\n| Metric | Value |\\n|---|---|\\n...",
  "discussion_questions": ["Question 1?", "Question 2?", ...]
}}

EXHIBITS CONFIG: {exhibits_config}

FACT SHEET:
{fact_sheet_json}
"""


def _question_count(audience: str) -> int:
    aud = (audience or "").lower()
    if "undergraduate" in aud or "bba" in aud:
        return 3
    return 5


def _audience_level(audience: str) -> str:
    aud = (audience or "").lower()
    if "undergraduate" in aud or "bba" in aud:
        return "undergraduate comprehension"
    if "c-suite" in aud or "executive" in aud:
        return "C-suite strategic synthesis"
    return "MBA-level strategic synthesis"


def run_agent_3(fact_sheet, ui_config: dict) -> dict:
    """
    Returns {"exhibits": str, "discussion_questions": list[str]}.
    """
    audience = ui_config.get("audience", "")
    num_q = _question_count(audience)

    prompt = _ANALYST_PROMPT.format(
        num_questions=num_q,
        audience_level=_audience_level(audience),
        exhibits_config=json.dumps(EXHIBITS_CONFIG),
        fact_sheet_json=fact_sheet.model_dump_json(indent=2),
    )

    result = generate_json(prompt)
    exhibits = result.get("exhibits", "") or ""
    questions = result.get("discussion_questions", []) or []

    if not isinstance(questions, list):
        questions = [str(questions)]

    # Skip exhibits if no numeric data in fact sheet
    has_numbers = any(
        c.isdigit() for c in (fact_sheet.revenue or "")
    ) or bool(fact_sheet.raw_facts)

    if EXHIBITS_CONFIG.get("skip_if_no_data") and not has_numbers and not exhibits.strip():
        exhibits = ""

    return {
        "exhibits": exhibits,
        "discussion_questions": questions[:num_q],
    }
