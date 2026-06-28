"""Filter FactSheet to facts relevant to the selected theme."""

from pipeline.agents.llm_client import generate_validated_json
from pipeline.models.schemas import FactSheet

_FILTER_PROMPT = """
You are a business analyst preparing a focused case study.

Given this FactSheet JSON and the selected theme "{theme}", return a FILTERED FactSheet JSON
containing ONLY facts relevant to theme "{theme}".

Rules:
- Always keep company_name, founding_year, industry, headquarters (if present).
- Keep revenue only if relevant to the theme or essential context.
- Filter challenges, interventions, outcomes, timeline_events, key_quotes, raw_facts, tagged_facts
  to those supporting theme "{theme}".
- Keep key_quotes that support the theme narrative.
- Set themes to a single-item list: ["{theme}"].

Return ONLY valid JSON matching the FactSheet schema.

FACT SHEET:
{fact_sheet_json}
"""


def filter_by_theme(fact_sheet: FactSheet, selected_theme: str) -> FactSheet:
    """Return a FactSheet filtered to the selected narrative theme."""
    if not selected_theme:
        return fact_sheet

    prompt = _FILTER_PROMPT.format(
        theme=selected_theme,
        fact_sheet_json=fact_sheet.model_dump_json(indent=2),
    )

    try:
        return generate_validated_json(prompt, FactSheet, max_retries=3)
    except Exception as e:
        print(f"[ThemeFilter] LLM filter failed ({e}), using rule-based fallback")
        return _rule_based_filter(fact_sheet, selected_theme)


def _rule_based_filter(fact_sheet: FactSheet, theme: str) -> FactSheet:
    """Fallback: keep items whose theme_tags or text mention the theme."""
    theme_lower = theme.lower()
    data = fact_sheet.model_dump()

    def matches(text: str) -> bool:
        return theme_lower in (text or "").lower()

    data["challenges"] = [c for c in data.get("challenges", []) if matches(c)]
    data["interventions"] = [i for i in data.get("interventions", []) if matches(i)]
    data["outcomes"] = [o for o in data.get("outcomes", []) if matches(o)]
    data["raw_facts"] = [f for f in data.get("raw_facts", []) if matches(f)]
    data["tagged_facts"] = [
        t for t in data.get("tagged_facts", [])
        if any(matches(tag) for tag in t.get("theme_tags", [])) or matches(t.get("fact", ""))
    ]
    data["timeline_events"] = [
        t for t in data.get("timeline_events", [])
        if any(matches(tag) for tag in t.get("theme_tags", [])) or matches(t.get("event", ""))
    ]
    data["key_quotes"] = [
        q for q in data.get("key_quotes", [])
        if any(matches(tag) for tag in q.get("theme_tags", [])) or matches(q.get("quote", ""))
    ]
    data["themes"] = [theme]

    # If filter removed everything, keep original lists (avoid empty narrative)
    if not any([data["challenges"], data["interventions"], data["outcomes"], data["raw_facts"]]):
        return fact_sheet

    return FactSheet(**data)
