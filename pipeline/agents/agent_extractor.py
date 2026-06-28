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
extract EVERY hard fact you can find.

EXTRACTION RULES:
1. Company name: Look in the title, header, "About Us", Chairman's message.
2. Financial figures: Revenue, profit, EBITDA, ROCE. Look for ₹, $, crore, million, %.
3. Dates: Founding year, reporting year (FY2025-26), milestone years.
4. Key people: Chairman, CEO, MD, CFO with full names AND titles.
5. Quotes: Text inside "..." from leadership messages. Include speaker name.
6. Challenges, Interventions, Outcomes: specific and factual.
7. Themes: Up to 5 STRATEGIC topics (e.g. "Decarbonisation", "Supply Chain Resilience").
8. tagged_facts: For each important fact, add theme_tags from the themes you identify.

If a value is unknown, use null for scalar fields and [] for list fields.
Do NOT omit any keys.

OUTPUT ONLY VALID JSON — no prose, no markdown fences.

{{
  "company_name": "full legal company name or null",
  "founding_year": "4-digit year string or null",
  "industry": "industry sector or null",
  "headquarters": "City, Country or null",
  "revenue": "revenue with currency and year or null",
  "key_people": ["Name (Title)"],
  "timeline_events": [
    {{
      "year": "string",
      "event": "description",
      "source": null,
      "theme_tags": []
    }}
  ],
  "challenges": ["challenge 1"],
  "interventions": ["initiative 1"],
  "outcomes": ["result 1"],
  "key_quotes": [
    {{
      "speaker": "Name",
      "quote": "text",
      "source": null,
      "theme_tags": []
    }}
  ],
  "themes": ["Theme 1", "Theme 2"],
  "raw_facts": ["other hard facts"],
  "tagged_facts": [
    {{
      "fact": "specific fact",
      "theme_tags": ["Theme 1"],
      "source": null
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
    }

    for p in partials:
        if not p:
            continue
        for field in ("company_name", "founding_year", "industry", "headquarters", "revenue"):
            if not merged[field] and p.get(field):
                merged[field] = p[field]

        for field in ("key_people", "challenges", "interventions", "outcomes", "raw_facts", "themes"):
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
