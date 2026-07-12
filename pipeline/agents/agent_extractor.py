"""
Agent 1 — Fact Extractor & Theme Discoverer
Two-pass: batch extraction → synthesis → Pydantic validation with LLM retry.
"""

import json
from typing import Callable, Optional

from pydantic import ValidationError

from pipeline.agents.llm_client import generate_json, generate_text
from pipeline.models.schemas import FactSheet

_EXTRACTION_PROMPT = """
You are a business document fact extractor for a case study generation tool.
Read the text below (extracted from an annual report or corporate document) and
extract EVERY hard fact you can find. Be exhaustive — it is better to over-extract
than to miss a fact. Each field below MUST be populated if the text supports it.

EXTRACTION RULES:
1. company_name: Look in title, header, "About Us", Chairman's message.
2. revenue: Look ONLY for TOTAL company financial revenue, turnover, or total sales expressed in currency (e.g. ¥ trillion, $ billion, ₹ crore). Do NOT extract operating income, profit, or revenue for a single business division/segment. Include currency symbol, unit (crore/million/billion/%), and year. If multiple figures exist, put the total company figure here. CRITICAL: Do NOT confuse unit sales volume (number of vehicles, products, or units sold) with financial revenue. If the text only provides sales in units (e.g. '10.3 million vehicles sold'), leave revenue as null — that is a production/sales count, NOT a financial figure.
3. raw_facts: List EVERY numerical or quantitative fact you can find — percentages, production numbers, employee counts, unit sales, market share, capacity figures, rankings, ratings. Include the context for each number AND the year it refers to (e.g. "2024 worldwide sales: 10,385,902 units"). RECENCY RULE: If the data source contains figures for multiple years (e.g. a column per year), you MUST prioritise the most recent year's figures. The most recent year column will be marked with "⚠️ MOST RECENT DATA COLUMN" in the source text — use THOSE figures as the primary facts. Always label each figure with its year so the case study does not confuse historical data with current performance. Do NOT skip any number. ARITHMETIC BAN: If a column is marked as "⚠️ WARNING: PARTIAL YEAR" or "CUMULATIVE" or "YTD", extract the number exactly as written — NEVER multiply, extrapolate, or annualise it to guess a full-year figure. Record it with a clear label such as "Jan–May 2026 cumulative worldwide sales: 4,140,444 units".
4. timeline_events: List EVERY dated event, milestone, product launch, policy change, or achievement mentioned. Each entry must have a year (even approximate like "2023") and a clear description.
5. challenges: List every CURRENT problem, obstacle, difficulty, or risk mentioned (e.g. operational, financial, regulatory). CRITICAL: Do NOT list historical challenges from decades ago (e.g. 1950s labor disputes, 1970s oil crisis) as current challenges. If the text mentions them purely as historical background, exclude them or place them in timeline_events, not here.
6. interventions: List every initiative, programme, investment, technology, process, or strategic change the company took in response to challenges. CRITICAL CAUSAL RULE: For each intervention, you MUST also capture (a) the strategic rationale — WHY this specific approach was chosen over alternatives, and (b) the mechanism — HOW it is expected to work. Format each entry as a SINGLE STRING (do not use a nested object/dict): "[Initiative name]: [what it is]. Rationale: [why chosen]. Mechanism: [how it works]. Expected outcome: [what it aims to achieve]."
7. outcomes: List every measurable or stated result, achievement, improvement, or outcome — including production milestones, market performance, and financial results. For each outcome, state the CAUSAL LINK in the same SINGLE STRING: which specific intervention drove this result and by what mechanism.
8. key_quotes: Extract ALL direct quotes (text inside quotation marks) from leadership, employees, or official statements. Include the full quote text and speaker name with title.
9. key_people: All CURRENT, named leaders/executives with their exact title. Only include people who are currently active at the company. Do NOT list historical figures, founders who passed away, or people who are no longer employed at the company. If a person is mentioned purely in a historical context (e.g. the creator of a business system who is no longer alive), exclude them.
10. themes: Up to 5 STRATEGIC topics reflected in this text.
11. tagged_facts: For EVERY fact in raw_facts, challenges, interventions, and outcomes, create a tagged_facts entry linking that fact to a theme.
12. strategic_initiatives: List EVERY named programme, brand launch, technology bet, or major strategic project (e.g. "Woven City", "ENGINE ReBORN", "bZ3X BEV launch"). Include its name, a rich description with all available details, the approximate year, and — critically — (a) the strategic rationale (WHY this initiative exists, what threat or opportunity it addresses), (b) the mechanism (HOW it works, not just what it is), and (c) which specific partners, technologies, or investments it relies on.
13. key_partnerships: List EVERY named external partner, joint venture, or strategic alliance. Include partner name, the domain of the partnership, and a brief description.
14. ANTI-HALLUCINATION RULE (ABSOLUTE): NEVER output the phrase '30 trillion' or '¥30 trillion' or any variant in any field (revenue, raw_facts, etc.) unless those exact words appear verbatim in the text you are reading. If no revenue figure is present in the text, set revenue to null. Do NOT estimate, infer, or calculate revenue from sales volumes, unit counts, or any other metric.

CRITICAL: Do NOT leave timeline_events, challenges, interventions, outcomes, key_quotes, raw_facts, strategic_initiatives, or key_partnerships as empty arrays if there is ANY relevant content in the text. These are the most important fields.

If a value is unknown, use null for scalar fields and [] for list fields.
Do NOT omit any keys.

OUTPUT ONLY VALID JSON — no prose, no markdown fences.

{{
  "company_name": "full legal company name or null",
  "founding_year": "4-digit year string or null",
  "industry": "industry sector or null",
  "headquarters": "City, Country or null",
  "revenue": "revenue with currency, unit, and year or null",
  "key_people": ["Name (Title)"],
  "timeline_events": [
    {{
      "year": "string",
      "event": "description",
      "source": null,
      "theme_tags": []
    }}
  ],
  "challenges": ["specific challenge description"],
  "interventions": ["specific initiative or action taken"],
  "outcomes": ["specific measurable or stated result"],
  "key_quotes": [
    {{
      "speaker": "Name (Title)",
      "quote": "exact text of the quote",
      "source": null,
      "theme_tags": []
    }}
  ],
  "themes": ["Theme 1", "Theme 2"],
  "raw_facts": ["every numerical or quantitative fact with context"],
  "tagged_facts": [
    {{
      "fact": "specific fact",
      "theme_tags": ["Theme 1"],
      "source": null
    }}
  ],
  "strategic_initiatives": [
    {{
      "name": "Programme Name",
      "description": "detailed description of what this initiative is and what it aims to achieve",
      "year": "year or null",
      "theme_tags": []
    }}
  ],
  "key_partnerships": [
    {{
      "partner": "Partner Organisation Name",
      "area": "domain (e.g. hydrogen, batteries, supply chain)",
      "description": "brief explanation of the partnership"
    }}
  ]
}}

TEXT TO ANALYSE:
{text}
"""
_SYNTHESIS_PROMPT = """
You are a senior business analyst. Below are partial fact extractions from
different sections of the same corporate document.

SYNTHESISE them into ONE coherent, deduplicated FactSheet.

Rules:
- company_name: most complete official legal name.
- Deduplicate lists semantically; keep most specific wording.
- themes: You MUST output exactly 3-5 distinct STRATEGIC themes. Review all themes from the partial extractions and synthesise the best 3-5 that represent the most important strategic storylines across the whole document. Do NOT return null, do NOT return an empty list, do NOT omit this field. If partials have conflicting or overlapping themes, consolidate them intelligently into 3-5 clean strategic themes. This field is critical for the user interface.
- tagged_facts: merge and tag facts with relevant theme_tags.
- CRITICAL — do NOT discard or empty any of these fields during deduplication:
  timeline_events, challenges, interventions, outcomes, key_quotes, raw_facts,
  strategic_initiatives, key_partnerships.
  If the same event appears multiple times with slightly different wording, keep
  the most detailed version. Never output an empty list for these fields if any
  partial had data in them.

ANTI-TRUNCATION RULE (most important):
Before you output, count the total items in EACH of the following fields
across ALL partials: challenges, interventions, outcomes, raw_facts, strategic_initiatives.
Your output for EACH of these fields MUST contain AT LEAST that many UNIQUE items
(after deduplication). You are NOT allowed to summarise, compress, or drop any item
from any of these lists. Rules per field:
- raw_facts: every distinct numerical or quantitative fact must survive — especially
  specific performance specs (e.g. "20-minute charge time", "40% cost reduction",
  "200 fuel-cell trucks operational"). Do NOT merge two different figures into one entry.
- strategic_initiatives: every named programme, platform, or R&D initiative must survive —
  including software-defined vehicles (SDVs), motorsports programmes, platform architecture
  (e.g. TNGA), and any other named strategic project. Do NOT drop an initiative just because
  a similar one exists; keep the most detailed version of each distinct named initiative.
- challenges / interventions / outcomes: same rule as above — keep every distinct item,
  verbatim from whichever partial contains the most detail.

OUTPUT ONLY VALID JSON with the same structure as input fragments.

PARTIAL EXTRACTIONS:
{partials_json}
"""

_VALIDATION_RETRY_PROMPT = """
You produced invalid JSON for a FactSheet. Fix ALL schema errors and return ONLY valid JSON.

Schema errors:
{errors}

Invalid data:
{data_json}

Required structure — same fields as before including tagged_facts array.
"""


def _process_batch(chunks: list[str], batch_num: int) -> dict:
    combined = "\n\n".join(chunks)
    prompt = _EXTRACTION_PROMPT.format(text=combined)
    result = None #changed: added result = None
    try:
        result = generate_json(prompt)
        if result:
            company = result.get("company_name") or "—"
            themes = result.get("themes") or []
            print(f"[Agent 1] Batch {batch_num} OK — company: {company!r}, themes: {themes}")
    except Exception as e:
        print(f"[Agent 1] Batch {batch_num} error: {e}")
    return result or {}

def _synthesise(partials: list[dict]) -> dict:
    valid = [p for p in partials if p]
    if not valid:
        return {}

    partials_json = json.dumps(valid, indent=2, ensure_ascii=False)
    prompt = _SYNTHESIS_PROMPT.format(partials_json=partials_json)

    try:
        result = generate_json(prompt)
        if result:
            # Safety net: if synthesis dropped themes, harvest them from partials
            if not result.get("themes"):
                all_themes = []
                seen = set()
                for p in valid:
                    for t in p.get("themes", []):
                        if t and t not in seen:
                            all_themes.append(t)
                            seen.add(t)
                result["themes"] = all_themes[:5] if all_themes else ["General Business Analysis"]
                print(f"[Agent 1] Synthesis dropped themes — harvested {len(result['themes'])} from partials")
            print("[Agent 1] Synthesis OK")
            return result
    except Exception as e:
        print(f"[Agent 1] Synthesis error: {e}")

    print("[Agent 1] Synthesis failed — falling back to heuristic merge")
    return _heuristic_merge(valid)


def _heuristic_merge(partials: list[dict]) -> dict:
    merged = {
        "company_name": "",
        "founding_year": None,
        "industry": None,
        "headquarters": None,
        "revenue": None,
        "key_people": [],
        "timeline_events": [],
        "challenges": [],
        "interventions": [],
        "outcomes": [],
        "key_quotes": [],
        "themes": [],
        "raw_facts": [],
        "tagged_facts": [],
        "strategic_initiatives": [],
        "key_partnerships": [],
    }

    for p in partials:
        if not p:
            continue
        for field in ("company_name", "founding_year", "industry", "headquarters", "revenue"):
            if not merged[field] and p.get(field):
                merged[field] = p[field]

        for field in ("key_people", "challenges", "interventions", "outcomes", "raw_facts", "themes", "strategic_initiatives", "key_partnerships"):
            seen = {str(x) for x in merged[field]}
            for item in p.get(field, []):
                if str(item) not in seen:
                    merged[field].append(item)
                    seen.add(str(item))

        for item in p.get("timeline_events", []):
            if isinstance(item, dict) and not any(
                t.get("year") == item.get("year") and t.get("event") == item.get("event")
                for t in merged["timeline_events"]
            ):
                merged["timeline_events"].append(item)

        for item in p.get("key_quotes", []):
            if isinstance(item, dict) and not any(
                q.get("speaker") == item.get("speaker") and q.get("quote") == item.get("quote")
                for q in merged["key_quotes"]
            ):
                merged["key_quotes"].append(item)

        for item in p.get("tagged_facts", []):
            if isinstance(item, dict):
                merged["tagged_facts"].append(item)

    return merged


def _normalise_for_validation(merged: dict, partials: list[dict] = None) -> dict:
    if not merged.get("company_name"):
        merged["company_name"] = "Unknown Company"

    # Themes: if synthesis returned null/empty, harvest from partials then fall back
    if not merged.get("themes"):
        if partials:
            all_themes = []
            seen = set()
            for p in (partials or []):
                for t in p.get("themes", []):
                    if t and t not in seen:
                        all_themes.append(t)
                        seen.add(t)
            merged["themes"] = all_themes[:5] if all_themes else ["General Business Analysis"]
        else:
            merged["themes"] = ["General Business Analysis"]

    list_fields = (
        "key_people", "timeline_events", "challenges", "interventions",
        "outcomes", "key_quotes", "themes", "raw_facts", "tagged_facts",
        "strategic_initiatives", "key_partnerships",
    )
    for field in list_fields:
        if not isinstance(merged.get(field), list):
            merged[field] = []

    # Ensure pure string fields are actually strings (not dicts).
    for field in ("challenges", "interventions", "outcomes", "raw_facts", "themes", "key_people"):
        merged[field] = [
            str(item) if not isinstance(item, dict) else " ".join(f"{v}" for v in item.values())
            for item in merged[field]
        ]

    merged["timeline_events"] = [
        item if isinstance(item, dict) else {"year": None, "event": str(item), "source": None, "theme_tags": []}
        for item in merged.get("timeline_events", [])
    ]
    merged["key_quotes"] = [
        item if isinstance(item, dict) else {"speaker": "Unknown", "quote": str(item), "source": None, "theme_tags": []}
        for item in merged.get("key_quotes", [])
    ]
    merged["tagged_facts"] = [
        item if isinstance(item, dict) else {"fact": str(item), "theme_tags": [], "source": None}
        for item in merged.get("tagged_facts", [])
    ]
    merged["strategic_initiatives"] = [
        item if isinstance(item, dict) else {"name": str(item), "description": "", "year": None, "theme_tags": []}
        for item in merged.get("strategic_initiatives", [])
    ]
    merged["key_partnerships"] = [
        item if isinstance(item, dict) else {"partner": str(item), "area": "", "description": None}
        for item in merged.get("key_partnerships", [])
    ]
    return merged


def _validate_with_retry(merged: dict, partials: list[dict] = None, max_retries: int = 3) -> FactSheet:
    data = _normalise_for_validation(dict(merged), partials=partials)
    last_error = ""

    for attempt in range(max_retries):
        try:
            return FactSheet(**data)
        except ValidationError as e:
            last_error = str(e)
            print(f"[Agent 1] Pydantic validation error attempt {attempt + 1}: {e}")
            try:
                fix_prompt = _VALIDATION_RETRY_PROMPT.format(
                    errors=last_error,
                    data_json=json.dumps(data, indent=2, ensure_ascii=False),
                )
                fixed = generate_json(fix_prompt)
                if fixed:
                    data = _normalise_for_validation(fixed)
            except Exception as fix_err:
                print(f"[Agent 1] Validation retry LLM call failed: {fix_err}")

    raise ValueError(f"Agent 1 failed to produce a valid FactSheet after {max_retries} attempts: {last_error}")


def run_agent_1(
    chunks: list[str],
    batch_size: int = 5,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> FactSheet:
    """
    Two-pass extraction pipeline.
    on_progress(batch_num, total_batches) called after each Pass 1 batch.
    """
    if not chunks:
        raise ValueError("No chunks provided to Agent 1.")

    total = len(chunks)
    total_batches = (total + batch_size - 1) // batch_size
    print(f"[Agent 1] Pass 1: {total} chunks → {total_batches} batches")

    partials = []
    for i in range(0, total, batch_size):
        batch = chunks[i: i + batch_size]
        batch_num = (i // batch_size) + 1
        result = _process_batch(batch, batch_num)
        partials.append(result)
        if on_progress:
            on_progress(batch_num, total_batches)
    non_empty = sum(1 for p in partials if p)  # count batches that returned actual data
    print(f"[Agent 1] Pass 1 complete: {non_empty}/{total_batches} batches returned data")

    if non_empty == 0:
        raise ValueError(
            "No facts extracted — check that you uploaded a PDF annual report, "
            "not a homepage URL. Ensure extraction completed with at least 500 characters."
        )

    if on_progress:
        on_progress(total_batches, total_batches)

    print("[Agent 1] Starting Pass 2: synthesis...")
    merged = _synthesise(partials)

    print(f"[Agent 1] Result: company={merged.get('company_name')!r}, themes={merged.get('themes')}")
    return _validate_with_retry(merged, partials=partials)
