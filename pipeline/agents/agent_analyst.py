"""Agent 3 — Analyst: exhibits (Markdown tables) and discussion questions."""

import json

from pipeline.agents.llm_client import generate_json
from config import EXHIBITS_CONFIG

_ANALYST_PROMPT = """
You are a business case study analyst. Generate comprehensive exhibits and discussion questions from the FactSheet ONLY.

EXHIBIT RULES:
- Generate MULTIPLE focused, data-rich exhibits. Target 6 highly detailed exhibits total.
- Each exhibit must be a properly formatted Markdown table with a bold heading above it.
- Do NOT invent numbers. Use ONLY data from the FactSheet.
- If a category has no data, skip that exhibit. Do NOT generate empty tables.
- DO NOT generate purely qualitative exhibits (no Quotes, no generic Key People lists).
- TEMPORAL METADATA RULE (CRITICAL): If a raw fact includes a time qualifier (e.g. "Q1", "Jan–May 2026", "YTD", "Cumulative", "FY2025"), that qualifier MUST appear verbatim in the "Context" or "Period" column of the table. Never strip or omit the time period from any data point.
- DATA PRECISION RULE: Copy numbers exactly as they appear in raw_facts. Never round or convert units (e.g. write 10,823,000 not ~10.8M) UNLESS the source data itself explicitly uses '~' or '>' (e.g. '>50%', '~200'). If the source uses symbols, you may use them.
- SEGMENT SCOPE RULE (CRITICAL): If a raw fact is scoped to a segment, brand, region, or country (e.g. "electrified vehicles", "Lexus", "Vietnam"), that scope MUST appear in the Metric or Context column. NEVER present a segment/country figure or growth rate as a company-wide total.
{privacy_rule}
{brevity_rule}

Generate exhibits in this priority order (include ALL for which data exists):

1. **Financial Performance**: All revenue, profit, operating income, and financial figures.
   ⚠️ CRITICAL: If there are no explicit financial figures (revenue/profit/margins) in the FactSheet, SKIP this exhibit. Do NOT generate a row that says "Revenue: Significant" or any vague placeholder.
   Columns: Metric | Value | Period | Context.

2. **Sales, Production & Product Breakdown**: All unit sales, production volumes, market share, and deployment figures.
   This MUST include vehicle/product counts (including sub-category breakdowns like HEV vs BEV vs PHEV if available) and regional breakdowns. Include ALL relevant rows — do not drop rows to make room.
   Columns: Metric/Segment | Units/Value | Period.
   NOTE: Year-on-year comparisons belong in the dedicated Trend Analysis exhibit (Exhibit 3), not here.

3. **Trend Analysis / Year-on-Year Comparison**: If the FactSheet contains data for more than one year or period, generate a dedicated trend table showing how key metrics changed over time. This is a mandatory exhibit if ANY multi-year or multi-period data exists.
   Columns: Metric | [Earliest Period] | [Latest Period] | Change / Trend.

4. **Timeline of Key Events**: A chronological exhibit of all major milestones, launches, and strategic decisions extracted from timeline_events. Include every event with a year.
   Columns: Year | Event | Strategic Significance.

5. **Market / Competitive Comparison**: If there is data about market share, competitors, rankings, or industry scale.
   Columns: Category | Company/Metric | Value | Period.

6. **Cost / Process Breakdown**: If there is data about operational efficiency, cost reductions, supply chain metrics, or process improvements.
   Columns: Process/Area | Metric | Improvement/Impact | Period.

7. **Strategic Investments & Targets**: MANDATORY if the FactSheet contains ANY strategic targets, GHG reduction commitments, technology goals, or investment figures. Do NOT skip this exhibit if such data exists — even partial data warrants inclusion.
   Columns: Area/Initiative | Target/Investment | Deadline/Impact.

8. **Key Partnerships & Collaborations**: MANDATORY if the FactSheet contains ANY entries in key_partnerships. Include every partner by name with their collaboration area and a specific description. Do not summarize multiple partners into one generic row.
   Columns: Partner | Area of Collaboration | Description/Details.

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

    # Executive Summary purpose → fewer, briefer exhibits
    purpose = (ui_config.get("purpose") or "").lower()
    if "executive summary" in purpose:
        brevity_rule = (
            "- BREVITY RULE (ACTIVE — Purpose is Executive Summary): Generate at most 2-3 "
            "concise exhibits covering only the most decision-critical data. Each table must "
            "stay under 8 rows. Prioritise the Financial Performance and Trend Analysis exhibits; "
            "skip the rest unless essential."
        )
    else:
        brevity_rule = ""

    # Build the privacy masking rule based on UI config
    if ui_config.get("data_privacy"):
        privacy_rule = (
            "- DATA PRIVACY RULE (ACTIVE): Replace ALL exact financial figures and "
            "specific numerical values in the tables with directional bands "
            "(e.g. \"> 10 Million units\", \"increased significantly\", \"high double-digit growth\"). "
            "Do NOT include any exact numbers. Do NOT fabricate percentages."
        )
    else:
        privacy_rule = "- DATA PRIVACY RULE: Keep all exact figures from the FactSheet as-is."

    prompt = _ANALYST_PROMPT.format(
        num_questions=num_q,
        audience_level=_audience_level(audience),
        theme=theme,
        privacy_rule=privacy_rule,
        brevity_rule=brevity_rule,
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
