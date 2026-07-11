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


def _narrative_prompt(fact_sheet_json: str, ui_config: dict, case_template: dict, few_shot: dict) -> str:
    ctx = _build_system_context(ui_config, case_template, few_shot)
    return f"""
You are a case study storyteller. Write flowing prose for ALL required sections.
Use ONLY facts from the FactSheet. Do NOT invent numbers or facts.
Do NOT invent named entities — no founder names, competitor names, partner organisations,
people, products, or awards unless they appear in the FactSheet. If a section asks for something
absent from the FactSheet (e.g. competitors, founder), describe it generically ("established
competitors", "in its early years") rather than fabricating a name.
Write in third-person past tense. Weave in key_quotes where appropriate.
Respect word limits from the template. Apply tone and audience from UI config.

{ctx}

Return ONLY valid JSON — a dict keyed by section id:
{{
  "background": "markdown prose...",
  "industry_context": "...",
  "challenge": "...",
  "intervention": "...",
  "results": "...",
  "learnings": "..."
}}

FACT SHEET:
{fact_sheet_json}
"""


def _section_prompt(section_id: str, fact_sheet_json: str, ui_config: dict, case_template: dict, few_shot: dict) -> str:
    ctx = _build_system_context(ui_config, case_template, few_shot)
    section = next((s for s in case_template.get("sections", []) if s.get("id") == section_id), {})
    return f"""
You are a professional case study author. Generate ONLY the "{section_id}" section ({section.get("title", section_id)}).

CRITICAL DATA RULE: You MUST aggressively weave numerical figures, percentages, dates, and quantitative metrics from the FactSheet into your prose. Do NOT write purely qualitative prose if numbers are available in raw_facts, outcomes, or tagged_facts.

CRITICAL ANTI-HALLUCINATION RULES:
1. Do NOT invent operational details (e.g., "brainstorming sessions", "workshops", "restructured workforce", "marketing campaigns", "budget allocated") unless explicitly stated in the FactSheet.
2. Do NOT invent narrative drama or emotions (e.g., "struggling", "under pressure", "lagging", "fraught with challenges") unless those exact words appear in the FactSheet. If the FactSheet describes a proactive, confident strategy, present it as confident and deliberate — not reactive.
3. Do NOT draw unsupported cautionary conclusions. Stick strictly to the tone expressed in the source data.
4. Use ONLY named entities (people, products, partners, awards, programmes) that explicitly appear in the FactSheet. Describe anything absent generically.

TONE AND VOICE RULES:
5. Use ACTIVE VOICE throughout. Write "Toyota launched the bZ3X in China" not "The bZ3X was launched in China by Toyota".
6. Match the STRATEGIC CONFIDENCE of the source document. Position the company as executing a deliberate, principled strategy — not reacting to a crisis.
7. If the FactSheet contains unique terminology from the source document (e.g., "multi-pathway strategy", "monozukuri", "genba", "Mobility for All", "region-centered management"), USE THOSE EXACT TERMS — do not paraphrase them into generic equivalents.
8. Use PRECISE powertrain terminology: use BEV, PHEV, HEV, FCEV specifically — never the generic term "EV" unless the source uses it.

IMPORTANT: strategic_initiatives in the FactSheet contains named programmes (e.g. Woven City, ENGINE ReBORN). You MUST write substantively about these in the intervention/results/background sections. key_partnerships contains named external partners — mention them by name.

Word limits: min {section.get("word_count_min", 200)}, max {section.get("word_count_max", 1200)}.

{ctx}

Return ONLY valid JSON: {{ "{section_id}": "markdown prose for this section only" }}

FACT SHEET:
{fact_sheet_json}
"""


def run_agent_2(fact_sheet, ui_config: dict) -> dict:
    """Generate all narrative sections sequentially. Returns dict section_id -> markdown."""
    case_template, few_shot = _load_templates()
    narrative = {}
    fact_sheet_json = fact_sheet.model_dump_json(indent=2)
    
    for section_id in _SECTION_IDS:
        print(f"[Agent 2] Generating section: {section_id}...")
        prompt = _section_prompt(
            section_id,
            fact_sheet_json,
            ui_config,
            case_template,
            few_shot,
        )
        result = generate_json(prompt)
        narrative[section_id] = result.get(section_id, "")
        
    return narrative


def regenerate_section(section_id: str, fact_sheet, ui_config: dict, existing_narrative: dict) -> dict:
    """Regenerate one section; return updated narrative dict."""
    if section_id not in _SECTION_IDS:
        raise ValueError(f"Unknown section: {section_id}")

    case_template, few_shot = _load_templates()
    prompt = _section_prompt(
        section_id,
        fact_sheet.model_dump_json(indent=2),
        ui_config,
        case_template,
        few_shot,
    )
    result = generate_json(prompt)
    updated = dict(existing_narrative)
    updated[section_id] = result.get(section_id, updated.get(section_id, ""))
    return updated
