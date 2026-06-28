"""Agent 4 — Editor: merge, fact-check, bias, privacy, citations."""

import re
from datetime import datetime

from pipeline.agents.llm_client import generate_text
from pipeline.models.schemas import FactSheet

_SECTION_ORDER = [
    ("background", "Company Background"),
    ("industry_context", "Industry Context"),
    ("challenge", "The Challenge"),
    ("intervention", "Intervention / Approach"),
    ("results", "Results & Impact"),
    ("learnings", "Learning Outcomes"),
]


def _merge_document(
    narrative: dict,
    exhibits: str,
    discussion_questions: list,
    company_name: str,
    selected_theme: str,
) -> str:
    parts = [f"# {company_name}: {selected_theme}\n"]

    for section_id, title in _SECTION_ORDER:
        body = narrative.get(section_id, "").strip()
        if body:
            parts.append(f"\n## {title}\n\n{body}\n")

    if exhibits and exhibits.strip():
        # Strip a leading "## Exhibits" the model may already have emitted, so we
        # don't end up with two stacked headings.
        ex = re.sub(r"^\s*#{1,6}\s*Exhibits\s*\n+", "", exhibits.strip(), flags=re.IGNORECASE)
        parts.append(f"\n## Exhibits\n\n{ex.strip()}\n")

    if discussion_questions:
        parts.append("\n## Discussion Questions\n")
        for i, q in enumerate(discussion_questions, 1):
            parts.append(f"{i}. {q}\n")

    return "\n".join(parts)


def _fact_sheet_text(fact_sheet: FactSheet) -> str:
    return fact_sheet.model_dump_json()


def _citation_year(fact_sheet: FactSheet) -> str:
    """Best-guess publication year: latest year mentioned in revenue/timeline,
    capped at the current year. Falls back to the current year (NOT the founding
    year, which would mis-date every reference)."""
    blob = " ".join(
        [fact_sheet.revenue or ""] + [(e.year or "") for e in fact_sheet.timeline_events]
    )
    current = datetime.now().year
    years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", blob)]
    years = [y for y in years if y <= current]
    return str(max(years)) if years else str(current)


def _build_references(
    master_transcript: dict,
    fact_sheet: FactSheet,
    citation_format: str,
    company_name: str,
) -> str:
    lines = ["\n## References\n"]
    sources = list(master_transcript.keys()) if isinstance(master_transcript, dict) else []
    year = _citation_year(fact_sheet)
    # Avoid "Ltd.." when the company name already ends in a period.
    name = (company_name or "Company").rstrip(".")

    for i, source in enumerate(sources, 1):
        fmt = (citation_format or "APA (7th Edition)").lower()
        if "ifqm" in fmt:
            lines.append(f"{i}. {name} ({year}). *{source}*. Retrieved from company records.")
        elif "mla" in fmt:
            lines.append(f"{i}. {name}. *{source}*. {year}.")
        elif "chicago" in fmt:
            lines.append(f"{i}. {name}, *{source}* ({year}).")
        else:
            lines.append(f"{i}. {name}. ({year}). *{source}*.")

    if not sources:
        lines.append(f"1. {name}. ({year}). Source documents provided by user.")

    return "\n".join(lines) + "\n"


def run_agent_4(
    narrative: dict,
    exhibits: str,
    discussion_questions: list,
    fact_sheet: FactSheet,
    filtered_fact_sheet: FactSheet,
    ui_config: dict,
    master_transcript: dict,
) -> str:
    """
    Merge narrative + exhibits, fact-check, de-bias, privacy mask, add citations.
    Returns final_markdown string.
    """
    company = filtered_fact_sheet.company_name or fact_sheet.company_name
    theme = ui_config.get("selected_theme") or ui_config.get("theme") or "Case Study"

    merged = _merge_document(narrative, exhibits, discussion_questions, company, theme)

    prompt = f"""
You are an academic case study editor and fact-checker.

TASKS (apply in order):
1. FACT-CHECK: Compare every number and date in the narrative against the ORIGINAL FactSheet below.
   Remove or rewrite sentences with figures NOT found in the FactSheet.
2. BIAS: Neutralize unsupported superlatives (e.g. "best", "revolutionary") unless backed by FactSheet data.
3. PRIVACY: {"Replace exact financial figures with directional language (e.g. 'increased significantly'). Do NOT fabricate percentages." if ui_config.get("data_privacy") else "Keep exact figures from the FactSheet."}
4. Preserve direct quotes and section structure (## headings).
5. Do NOT add a References section — it will be appended separately.

Return the FULL edited Markdown document only. No explanation.

ORIGINAL FACT SHEET (for verification):
{_fact_sheet_text(fact_sheet)}

DRAFT DOCUMENT:
{merged}
"""

    try:
        edited = generate_text(prompt)
    except Exception as e:
        print(f"[Agent 4] LLM edit failed ({e}), using unedited merge")
        edited = merged

    refs = _build_references(
        master_transcript,
        fact_sheet,
        ui_config.get("citation", "APA (7th Edition)"),
        company,
    )

    if "## References" not in edited:
        edited = edited.rstrip() + refs

    return edited
