"""Agent 3 — Analyst: exhibits (Markdown tables) and discussion questions."""

import json

from pipeline.agents.llm_client import generate_json
from config import EXHIBITS_CONFIG

_ANALYST_PROMPT = """
You are a business case study analyst. Generate comprehensive exhibits and discussion questions from the FactSheet ONLY.

EXHIBIT RULES:
- Generate AS MANY exhibits as the data supports (target 6-12).
- Each exhibit must be a properly formatted Markdown table with a bold heading above it.
- Do NOT invent numbers. Use ONLY data from the FactSheet.
- If a category has no data, skip that exhibit.

Generate exhibits in this priority order (include all for which data exists):

1. **Key Company Facts**: A two-column table of core company statistics (founding year, HQ, industry, revenue, employee count, key metrics from raw_facts and outcomes).

2. **Key Metrics & Data**: All numerical figures, percentages, financials, and production metrics from raw_facts, outcomes, and tagged_facts. Columns: Metric | Value | Context.

3. **Key People**: From key_people. Columns: Name | Role/Title.

4. **Strategic Initiatives**: From strategic_initiatives. Columns: Initiative | Description | Year. Write full, rich descriptions.

5. **Key Partnerships**: From key_partnerships. Columns: Partner | Domain | Description.

6. **Timeline of Key Events**: From timeline_events, sorted chronologically. Columns: Year | Event.

7. **Key Challenges**: From challenges. Columns: # | Challenge.

8. **Key Interventions**: From interventions. Columns: # | Intervention / Approach.

9. **Key Outcomes & Results**: From outcomes. Columns: # | Outcome.

10. **Key Quotes**: From key_quotes. Columns: Quote | Speaker.

11. **Carbon Neutrality / Sustainability Targets** (if data exists in raw_facts or outcomes): Columns: Target | Value | Year.

12. **Technology Comparison** (if battery, engine, or technology comparison data exists in raw_facts or strategic_initiatives): Columns: Technology | Specification | Performance.

Format all exhibits as:
**Exhibit N: [Title]**
| Column 1 | Column 2 | ... |
|---|---|...|
| value | value | ... |

- discussion_questions: {num_questions} open-ended, thought-provoking questions for a {audience_level} audience, aligned to the selected theme: {theme}.
- Questions should encourage critical analysis, not just factual recall.

Return ONLY valid JSON:
{{
  "exhibits": "**Exhibit 1: ...**\\n\\n| ... |\\n\\n**Exhibit 2: ...**\\n\\n...",
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
    theme = ui_config.get("theme") or ui_config.get("selected_theme") or "General Business Analysis"
    num_q = _question_count(audience)

    prompt = _ANALYST_PROMPT.format(
        num_questions=num_q,
        audience_level=_audience_level(audience),
        theme=theme,
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
