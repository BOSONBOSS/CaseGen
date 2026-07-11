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
2. revenue: Look ONLY for TOTAL company revenue, turnover, or total sales. Do NOT extract operating income, profit, or revenue for a single business division/segment. Include currency symbol, unit (crore/million/billion/%), and year. If multiple figures exist, put the total company figure here.
3. raw_facts: List EVERY numerical or quantitative fact you can find — percentages, production numbers, employee counts, unit sales, market share, capacity figures, rankings, ratings. Include the context for each number (e.g. "200 fuel-cell electric trucks operational as of December 2025"). Do NOT skip any number.
4. timeline_events: List EVERY dated event, milestone, product launch, policy change, or achievement mentioned. Each entry must have a year (even approximate like "2023") and a clear description.
5. challenges: List every problem, obstacle, difficulty, or risk mentioned — operational, financial, regulatory, competitive, or strategic.
6. interventions: List every initiative, programme, investment, technology, process, or strategic change the company took in response to challenges.
7. outcomes: List every measurable or stated result, achievement, improvement, or outcome — including production milestones, market performance, and financial results.
8. key_quotes: Extract ALL direct quotes (text inside quotation marks) from leadership, employees, or official statements. Include the full quote text and speaker name with title.
9. key_people: All named leaders/executives with their exact title.
10. themes: Up to 5 STRATEGIC topics reflected in this text.
11. tagged_facts: For EVERY fact in raw_facts, challenges, interventions, and outcomes, create a tagged_facts entry linking that fact to a theme.
12. strategic_initiatives: List EVERY named programme, brand launch, technology bet, or major strategic project (e.g. "Woven City", "ENGINE ReBORN", "bZ3X BEV launch"). Include its name, a rich description with all available details, and approximate year.
13. key_partnerships: List EVERY named external partner, joint venture, or strategic alliance. Include partner name, the domain of the partnership, and a brief description.

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
- themes: exactly 3-5 distinct STRATEGIC themes for the user to pick from.
- tagged_facts: merge and tag facts with relevant theme_tags.
- CRITICAL — do NOT discard or empty any of these fields during deduplication:
  timeline_events, challenges, interventions, outcomes, key_quotes, raw_facts,
  strategic_initiatives, key_partnerships.
  If the same event appears multiple times with slightly different wording, keep
  the most detailed version. Never output an empty list for these fields if any
  partial had data in them.

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


def _normalise_for_validation(merged: dict) -> dict:
    if not merged.get("company_name"):
        merged["company_name"] = "Unknown Company"
    if not merged.get("themes"):
        merged["themes"] = ["General Business Analysis"]

    list_fields = (
        "key_people", "timeline_events", "challenges", "interventions",
        "outcomes", "key_quotes", "themes", "raw_facts", "tagged_facts",
        "strategic_initiatives", "key_partnerships",
    )
    for field in list_fields:
        if not isinstance(merged.get(field), list):
            merged[field] = []

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


def _validate_with_retry(merged: dict, max_retries: int = 3) -> FactSheet:
    data = _normalise_for_validation(dict(merged))
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
    batch_size: int = 10,
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
    return _validate_with_retry(merged)
