"""Agent 3 — Analyst: exhibits (Markdown tables) and discussion questions."""

import json

from pipeline.agents.llm_client import generate_json
from config import EXHIBITS_CONFIG

_ANALYST_PROMPT = """
You are a business case study analyst. Generate comprehensive exhibits and discussion questions from the FactSheet ONLY.

EXHIBIT RULES:
- Generate ONLY data-rich, quantitative exhibits. Fewer, heavier tables are better (target 3-6 exhibits).
- Each exhibit must be a properly formatted Markdown table with a bold heading above it.
- Do NOT invent numbers. Use ONLY data from the FactSheet.
- If a category has no data, skip that exhibit.
- DO NOT generate categorical exhibits like Quotes, Key People, Timeline, Challenges, Interventions, or Outcomes.

Generate exhibits in this priority order (include all for which data exists):

1. **Financial Performance**: Extract all revenue, profit, operating income, and financial figures from the FactSheet.
   ⚠️ CRITICAL: If the FactSheet "revenue" field is null or empty AND there are no explicit financial figures (revenue/profit/margins) in raw_facts or outcomes, SKIP this exhibit entirely. Do NOT generate a row that says "Revenue: Significant" or any vague placeholder. Instead, fold any financial-adjacent data (e.g. operating income, value chain income, cost reduction percentages) into Exhibit 2 (Key Metrics).
   Columns: Metric | Value | Context.

2. **Key Metrics & Data**: All numerical figures from raw_facts, outcomes, and tagged_facts. This MUST include:
   - Production/deployment metrics (e.g. "200 fuel-cell trucks operational", "180 fuel-cell buses")
   - Technical performance specs (e.g. "1,000 km driving range", "20-minute charge time", "40% cost reduction")
   - Sales volume and market figures (e.g. "3.5 million BEV units target by 2030")
   - Any efficiency improvements (e.g. "10-12% fuel economy improvement", "20% hydrogen efficiency gain")
   Columns: Metric | Value | Context.

3. **Market / Competitive Comparison**: If there is data about market share, competitors, rankings, or industry scale. Columns: Category | Company/Metric | Value.

4. **Cost / Process Breakdown**: If there is data regarding operational efficiency, cost reductions, supply chain metrics, or process improvements. Columns: Process/Area | Metric | Improvement/Impact.

5. **Strategic Investments / Targets**: Any data related to investments, budget allocations, or quantifiable sustainability/technology targets. Columns: Area/Initiative | Target/Investment | Deadline/Impact.

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
    theme = ui_config.get("selected_theme") or "General Business Analysis"
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
