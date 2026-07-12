"""Agent 2 — Storyteller: writes case study narrative sections from FactSheet."""

import json

from pipeline.agents.llm_client import generate_json
from config import TEMPLATE_PATH, FEW_SHOT_PATH

_SECTION_IDS = [
    "background",
    "industry_context",
    "challenge",
    "intervention",
    "results",
    "learnings",
]

# Fix B: only send the FactSheet fields that are relevant to each section.
# This prevents the LLM from losing focus on items buried at the bottom of a large JSON.
_SECTION_FIELDS: dict[str, list[str]] = {
    "background": [
        "company_name", "founding_year", "industry", "headquarters", "revenue",
        "key_people", "timeline_events", "raw_facts", "strategic_initiatives",
        "key_partnerships", "key_quotes",
    ],
    "industry_context": [
        "company_name", "industry", "revenue", "raw_facts", "timeline_events",
        "tagged_facts", "key_quotes",
    ],
    "challenge": [
        "company_name", "challenges", "raw_facts", "timeline_events", "key_quotes",
    ],
    "intervention": [
        "company_name", "interventions", "strategic_initiatives", "key_partnerships",
        "key_people", "raw_facts", "key_quotes",
    ],
    "results": [
        "company_name", "outcomes", "raw_facts", "timeline_events", "key_quotes",
    ],
    "learnings": [
        "company_name", "challenges", "interventions", "outcomes", "themes", "key_quotes",
    ],
}


def _load_templates() -> tuple[dict, dict]:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        case_template = json.load(f)
    with open(FEW_SHOT_PATH, encoding="utf-8") as f:
        few_shot = json.load(f)
    return case_template, few_shot


def _build_system_context(ui_config: dict, case_template: dict, few_shot: dict) -> str:
    examples_block = json.dumps(few_shot, indent=2)[:8000]
    sections_block = json.dumps(case_template.get("sections", []), indent=2)
    return f"""
Style rules: {case_template.get("style_rules", "")}

Template sections (word limits apply):
{sections_block}

Few-shot examples (mimic tone and structure):
{examples_block}

UI config:
- Purpose: {ui_config.get("purpose", "")}
- Discipline: {ui_config.get("discipline", "")}
- Tone: {ui_config.get("tone", "")}
- Audience: {ui_config.get("audience", "")}
- Theme: {ui_config.get("selected_theme", "General Business Analysis")}
- Custom instructions: {ui_config.get("custom_instructions", "")}
"""


def _get_section_facts(section_id: str, fs_dict: dict) -> dict:
    """
    Fix B: return only the FactSheet keys relevant to this section so the LLM
    receives a focused, shorter JSON rather than the full 200-line blob.
    """
    relevant_keys = _SECTION_FIELDS.get(section_id, list(fs_dict.keys()))
    return {k: fs_dict.get(k) for k in relevant_keys}


def _build_enumeration_block(section_id: str, fs_dict: dict) -> str:
    """
    Fix C: pre-extract the mandatory coverage list for this section and render it
    as a numbered plain-text directive at the top of the prompt.
    The LLM receives an explicit count and cannot silently skip any item.
    """
    if section_id == "challenge":
        items = [str(c) for c in (fs_dict.get("challenges") or []) if c]
        label = "CHALLENGE"

    elif section_id == "intervention":
        items = [str(i) for i in (fs_dict.get("interventions") or []) if i]
        # Also surface strategic initiative names so they're explicitly listed
        for si in (fs_dict.get("strategic_initiatives") or []):
            name = si.get("name", "") if isinstance(si, dict) else str(si)
            if name and not any(name.lower() in item.lower() for item in items):
                desc = si.get("description", "") if isinstance(si, dict) else ""
                items.append(f"{name}" + (f" — {desc[:140]}" if desc else ""))
        label = "INTERVENTION / INITIATIVE"

    elif section_id == "results":
        items = [str(o) for o in (fs_dict.get("outcomes") or []) if o]
        label = "OUTCOME"

    else:
        return ""

    if not items:
        return ""

    lines = "\n".join(f"  {i + 1}. {item}" for i, item in enumerate(items))
    return (
        f"⚠️  MANDATORY COVERAGE — You MUST discuss ALL {len(items)} {label}S listed below "
        f"in this section. Omitting even one is a critical failure.\n{lines}\n"
    )


def _section_prompt(
    section_id: str,
    fact_sheet,           # FactSheet Pydantic model
    ui_config: dict,
    case_template: dict,
    few_shot: dict,
    exhibit_index: dict | None = None,
) -> str:
    ctx = _build_system_context(ui_config, case_template, few_shot)
    section = next((s for s in case_template.get("sections", []) if s.get("id") == section_id), {})

    # Fix B: build section-specific FactSheet subset
    fs_dict = fact_sheet.model_dump() if hasattr(fact_sheet, "model_dump") else fact_sheet
    section_facts = _get_section_facts(section_id, fs_dict)
    section_facts_json = json.dumps(section_facts, indent=2, ensure_ascii=False)

    # Fix C: explicit mandatory enumeration injected at top of prompt
    enumeration_block = _build_enumeration_block(section_id, fs_dict)

    # Exhibit cross-reference block
    if exhibit_index:
        exhibit_lines = "\n".join(
            f"  - Exhibit {num}: {title.title()}"
            for title, num in sorted(exhibit_index.items(), key=lambda x: x[1])
        )
        exhibit_ref_rule = f"""
EXHIBIT CROSS-REFERENCE RULE:
The following exhibits have been generated for this case study. When your prose naturally refers
to data that is tabulated in an exhibit (e.g. financial figures, key metrics, comparisons), you
MUST add an inline reference like "(see Exhibit N)" immediately after the relevant sentence.
Do NOT invent exhibit numbers. Only reference exhibits from this list:
{exhibit_lines}
"""
    else:
        exhibit_ref_rule = ""

    return f"""
You are a professional case study author. Generate ONLY the "{section_id}" section ({section.get("title", section_id)}).

{enumeration_block}
CRITICAL DATA RULE: You MUST aggressively weave numerical figures, percentages, dates, and quantitative metrics from the FactSheet into your prose. Do NOT write purely qualitative prose if numbers are available in raw_facts, outcomes, or tagged_facts.

CRITICAL ANTI-HALLUCINATION RULES:
1. Do NOT invent operational details (e.g., "brainstorming sessions", "workshops", "restructured workforce", "marketing campaigns", "budget allocated") unless explicitly stated in the FactSheet.
2. Do NOT invent narrative drama or emotions (e.g., "struggling", "under pressure", "lagging", "fraught with challenges") unless those exact words appear in the FactSheet. If the FactSheet describes a proactive, confident strategy, present it as confident and deliberate — not reactive.
3. Do NOT draw unsupported cautionary conclusions. Stick strictly to the tone expressed in the source data.
4. Use ONLY named entities (people, products, partners, awards, programmes) that explicitly appear in the FactSheet. Describe anything absent generically.
5. REVENUE RULE: If the FactSheet "revenue" field is null or empty, you MUST NOT write any total revenue figure (e.g. "¥30 trillion", "$273 billion"). Describe scale using only figures that DO appear in raw_facts or outcomes (e.g. annual sales volume, operating income). Never estimate or guess a revenue figure.
6. METRICS CLAIM RULE: NEVER write any sentence claiming "specific quantitative metrics were not disclosed" or "no figures were available". If the FactSheet has data in raw_facts, outcomes, or tagged_facts, it MUST be woven into the prose. If there is truly no data, simply omit that claim entirely.
7. QUOTE VERBATIM RULE: When quoting any person in prose, you MUST copy the quote CHARACTER-FOR-CHARACTER from the key_quotes list in the FactSheet. Do NOT paraphrase, condense, or add words. If you cannot find an exact match, do not use a quote — write the point as the author's own prose instead.

TONE AND VOICE RULES:
8. Use ACTIVE VOICE throughout. Write "Toyota launched the bZ3X in China" not "The bZ3X was launched in China by Toyota".
9. Match the STRATEGIC CONFIDENCE of the source document. Position the company as executing a deliberate, principled strategy — not reacting to a crisis.
10. If the FactSheet contains unique terminology from the source document (e.g., "multi-pathway strategy", "monozukuri", "genba", "Mobility for All", "region-centered management"), USE THOSE EXACT TERMS — do not paraphrase them into generic equivalents.
11. Use PRECISE powertrain terminology: use BEV, PHEV, HEV, FCEV specifically — never the generic term "EV" unless the source uses it.

IMPORTANT: strategic_initiatives in the FactSheet contains named programmes (e.g. Woven City, ENGINE ReBORN). You MUST write substantively about these in the intervention/results/background sections. key_partnerships contains named external partners — mention them by name.
{exhibit_ref_rule}
Word limits: min {section.get("word_count_min", 400)}, max {section.get("word_count_max", 2000)}.

{ctx}

Return ONLY valid JSON: {{ "{section_id}": "markdown prose for this section only" }}

FACT SHEET (section-relevant fields only):
{section_facts_json}
"""


def run_agent_2(fact_sheet, ui_config: dict, exhibit_index: dict | None = None, on_section_progress=None) -> dict:
    """Generate all narrative sections sequentially. Returns dict section_id -> markdown.
    on_section_progress(current, total) is called after each section completes.
    """
    case_template, few_shot = _load_templates()
    narrative = {}
    total = len(_SECTION_IDS)

    for i, section_id in enumerate(_SECTION_IDS):
        print(f"[Agent 2] Generating section: {section_id}...")
        prompt = _section_prompt(
            section_id,
            fact_sheet,
            ui_config,
            case_template,
            few_shot,
            exhibit_index=exhibit_index,
        )
        result = generate_json(prompt)
        narrative[section_id] = result.get(section_id, "")
        if on_section_progress:
            on_section_progress(i + 1, total)

    return narrative


def regenerate_section(
    section_id: str,
    fact_sheet,
    ui_config: dict,
    existing_narrative: dict,
    exhibit_index: dict | None = None,
) -> dict:
    """Regenerate one section; return updated narrative dict."""
    if section_id not in _SECTION_IDS:
        raise ValueError(f"Unknown section: {section_id}")

    case_template, few_shot = _load_templates()
    prompt = _section_prompt(
        section_id,
        fact_sheet,
        ui_config,
        case_template,
        few_shot,
        exhibit_index=exhibit_index,
    )
    result = generate_json(prompt)
    updated = dict(existing_narrative)
    updated[section_id] = result.get(section_id, updated.get(section_id, ""))
    return updated
