"""Agent 4 — Editor: merge, fact-check, bias, privacy, citations."""

import re
from datetime import datetime
from urllib.parse import urlparse

from pipeline.agents.llm_client import generate_text
from pipeline.models.schemas import FactSheet

# ---------------------------------------------------------------------------
# Deterministic hallucination scrubber
# The LLM sometimes ignores prompt-level rules and invents revenue/market
# figures (e.g. "¥30 trillion"). We catch these with regex AFTER the LLM
# writes, so they can never reach the final document.
# ---------------------------------------------------------------------------
_HALLUCINATION_PATTERNS = [
    # Any sentence containing a currency amount followed by "trillion"
    # e.g. "¥30 trillion", "$30 trillion", "USD 30 trillion"
    r"[^.!?\n]*?[¥$€£₹]\s*\d+[\d,.]*\s*trillion[^.!?\n]*[.!?]?",
    # Pattern without leading currency symbol: "30 trillion yen/dollars"
    r"[^.!?\n]*?\b\d+[\d,.]*\s*trillion\s+(?:yen|dollars?|euros?|yuan|rupees?)[^.!?\n]*[.!?]?",
    # Exhibit lines containing fabricated revenue (e.g. "Revenue: ¥30 trillion")
    r"[^\n]*revenue[^\n]*[¥$€£₹]\s*\d+[\d,.]*\s*trillion[^\n]*",
    # "projected/target revenue of ¥X trillion"
    r"[^.!?\n]*(?:projected|target|aimed)\s+(?:a\s+)?revenue[^.!?\n]*trillion[^.!?\n]*[.!?]?",
]
_HALLUCINATION_RE = re.compile(
    "|".join(f"(?:{p})" for p in _HALLUCINATION_PATTERNS),
    re.IGNORECASE | re.DOTALL,
)


def _scrub_hallucinations(text: str, fact_sheet: FactSheet) -> str:
    """Remove sentences that contain fabricated financial figures.

    We build a whitelist of EXACT 'currency+number+unit' tokens that appear
    in the FactSheet. Only matches whose currency+amount token is on this list
    are kept. This prevents '30' appearing in raw_facts (e.g. '30 years of
    HEV experience') from accidentally whitelisting '¥30 trillion'.
    """
    # Build whitelist of currency+amount+unit tokens from the FactSheet
    # e.g. if revenue = '¥37.4 trillion', we whitelist '¥37.4 trillion'
    currency_token_re = re.compile(
        r"[¥$€£₹]\s*[\d,.]+\s*(?:trillion|billion|million|crore)?"
        r"|\b[\d,.]+\s*(?:trillion|billion|million|crore)\s+(?:yen|dollars?|euros?|yuan|rupees?)",
        re.IGNORECASE,
    )
    whitelisted_tokens: set[str] = set()
    sources = [fact_sheet.revenue or ""] + (fact_sheet.raw_facts or [])
    for src in sources:
        for tok in currency_token_re.findall(src):
            whitelisted_tokens.add(tok.lower().replace(" ", ""))

    def _should_remove(match: re.Match) -> str:
        matched_tokens = currency_token_re.findall(match.group())
        for tok in matched_tokens:
            normalised = tok.lower().replace(" ", "")
            if normalised not in whitelisted_tokens:
                print(f"[Agent 4] 🛡️ Scrubbed hallucinated figure: {match.group()[:120]!r}")
                return ""  # fabricated — remove it
        return match.group()  # every token is sourced — keep it

    scrubbed = _HALLUCINATION_RE.sub(_should_remove, text)

    # ── NUCLEAR FALLBACK ──────────────────────────────────────────────────────
    # Even if '¥30 trillion' somehow entered the FactSheet whitelist through an
    # Agent 1 hallucination, we unconditionally strip any sentence that contains
    # the exact phrase "30 trillion". This is hardcoded Python — the LLM cannot
    # override it regardless of what it outputs.
    _THIRTY_TRILLION_RE = re.compile(
        r"[^.!?\n]*?\b30\s*trillion\b[^.!?\n]*[.!?]?",
        re.IGNORECASE,
    )
    def _nuclear_strip(m: re.Match) -> str:
        print(f"[Agent 4] 💥 NUCLEAR SCRUB — removed '30 trillion' sentence: {m.group()[:120]!r}")
        return ""
    scrubbed = _THIRTY_TRILLION_RE.sub(_nuclear_strip, scrubbed)
    # ─────────────────────────────────────────────────────────────────────────

    # Clean up any double blank lines left behind
    scrubbed = re.sub(r"\n{3,}", "\n\n", scrubbed)
    return scrubbed

def _strip_em_dashes(text: str) -> str:
    """Replace em/en dashes with plain hyphens (user style requirement).
    Runs deterministically on the final document so no LLM output can slip through."""
    text = re.sub(r"[ \t]*[\u2014\u2015][ \t]*", " - ", text)   # em dash / horizontal bar
    text = text.replace("\u2013", "-").replace("\u2012", "-")  # en dash / figure dash
    return text


_EXHIBIT_BLOCK_RE = re.compile(
    r"\*\*Exhibit\s+\d+[^\n]*\*\*[ \t]*\n+((?:\|[^\n]*\n?)*)",
)


def _remove_empty_exhibits(text: str) -> str:
    """Deterministically drop exhibits whose tables contain no data rows
    (header + separator only, or no table at all), then renumber the rest."""
    def _check(m: re.Match) -> str:
        table_lines = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
        _PLACEHOLDER_CELLS = {"", "-", "--", "n/a", "na", "none", "not disclosed", "not available", "no data"}
        data_rows = []
        for l in table_lines[1:]:
            if set(l.replace("|", "").strip()) <= {"-", ":", " "}:
                continue  # separator row
            cells = [c.strip().strip("*").lower() for c in l.strip().strip("|").split("|")]
            if all(c in _PLACEHOLDER_CELLS for c in cells):
                continue  # placeholder-only row
            data_rows.append(l)
        if not data_rows:
            print(f"[Agent 4] Removed empty exhibit: {m.group(0)[:80]!r}")
            return ""
        return m.group(0)

    cleaned = _EXHIBIT_BLOCK_RE.sub(_check, text)

    # Renumber surviving exhibits sequentially
    counter = {"n": 0}
    def _renumber(m: re.Match) -> str:
        counter["n"] += 1
        return f"**Exhibit {counter['n']}:"
    cleaned = re.sub(r"\*\*Exhibit\s+\d+\s*:", _renumber, cleaned)

    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _url_site_name(url: str) -> str:
    """Human-readable site name for embedding a link inside a citation sentence,
    e.g. 'https://global.toyota/pages/...' -> 'global.toyota'."""
    netloc = urlparse(url).netloc or url
    return netloc.removeprefix("www.")


_SECTION_ORDER = [
    ("background", "Company Background"),
    ("industry_context", "Industry Context"),
    ("challenge", "The Challenge"),
    ("intervention", "Intervention / Approach"),
    ("results", "Results & Impact"),
    ("learnings", "Learning Outcomes"),
]

def _pick_best_quote(key_quotes: list) -> tuple[str, str]:
    """
    Select the single most impactful verbatim quote for the case study header.
    Scores by: (1) speaker seniority -- Chairman/President/CEO rank highest,
               (2) quote length -- longer quotes tend to be more substantive.
    Returns (quote_text, speaker_label) or ("", "") if no suitable quote found.
    """
    SENIORITY = {
        "chairman": 10, "president": 9, "ceo": 9, "chief executive": 9,
        "coo": 7, "cfo": 7, "managing director": 7, "md": 7,
        "director": 5, "general manager": 4, "manager": 3,
    }
    MIN_QUOTE_LENGTH = 40  # skip one-liner slogans

    best_score = -1
    best_quote = ("", "")

    for q in key_quotes:
        q_text = q.quote if hasattr(q, "quote") else q.get("quote", "")
        q_speaker = q.speaker if hasattr(q, "speaker") else q.get("speaker", "")
        if not q_text or len(q_text) < MIN_QUOTE_LENGTH:
            continue
        speaker_lower = (q_speaker or "").lower()
        seniority_score = max(
            (v for k, v in SENIORITY.items() if k in speaker_lower),
            default=1,
        )
        length_score = min(len(q_text) / 50, 5)  # cap to avoid runaway length bias
        score = seniority_score + length_score
        if score > best_score:
            best_score = score
            best_quote = (q_text, q_speaker)

    return best_quote

def _merge_document(
    narrative: dict,
    exhibits: str,
    discussion_questions: list,
    company_name: str,
    selected_theme: str,
    fact_sheet: FactSheet,
) -> str:
    parts = [f"# {company_name}: {selected_theme}\n"]

    if fact_sheet.key_quotes:
        q_text, q_speaker = _pick_best_quote(fact_sheet.key_quotes)
        if q_text:
            parts.append(f"> \"{q_text}\" - *{q_speaker}*\n")

    for section_id, title in _SECTION_ORDER:
        body = narrative.get(section_id, "").strip()
        if body:
            # Strip a leading "## Title" the model may have emitted to prevent duplicate headings
            body = re.sub(rf"^\s*#{{1,6}}\s*(?:The\s+)?{re.escape(title)}\s*\n+", "", body, flags=re.IGNORECASE)
            body = re.sub(rf"^\s*#{{1,6}}\s*(?:The\s+)?{re.escape(section_id)}\s*\n+", "", body, flags=re.IGNORECASE)
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
        # Detect if the source is a URL
        is_url = source.startswith("http://") or source.startswith("https://")
        if is_url:
            site = _url_site_name(source)
            if "ifqm" in fmt:
                lines.append(f"{i}. {name} ({year}). Retrieved from the official [{site}]({source}) website.")
            elif "mla" in fmt:
                lines.append(f"{i}. {name}. *Web*. {year}. Available on the [{site}]({source}) website.")
            elif "chicago" in fmt:
                lines.append(f"{i}. {name}. {year}. Accessed via the [{site}]({source}) website.")
            else:  # APA default
                lines.append(f"{i}. {name}. ({year}). Retrieved from the official [{site}]({source}) website.")
        else:
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
    theme = ui_config.get("selected_theme") or "Case Study"

    merged = _merge_document(narrative, exhibits, discussion_questions, company, theme, filtered_fact_sheet)

    prompt = f"""
You are an academic case study editor and fact-checker.

TASKS (apply in order):
1. FACT-CHECK (numbers & dates): Compare every number and date in the narrative against the ORIGINAL FactSheet below.
   Remove or rewrite sentences with figures NOT found in the FactSheet.
2. FACT-CHECK (named entities): Verify every proper noun that states a FACT about the company —
   founder/founding person, named competitors, partner organisations, people and their titles,
   place names, product names, award names. If a named entity is NOT present anywhere in the
   FactSheet, it is fabricated: delete it or rewrite the sentence generically (e.g. replace
   "founded by J.R.D. Tata" with "founded in its early years", or "competitors such as X and Y"
   with "several established competitors"). Do NOT invent replacements. Generic, non-named
   industry context (e.g. "the steel sector faces decarbonisation pressure") may stay only if it
   contains no fabricated figures or names.
3. BIAS: Neutralize unsupported superlatives (e.g. "best", "revolutionary") unless backed by FactSheet data.
4. PRIVACY: {"Replace exact financial figures with directional language (e.g. 'increased significantly'). Do NOT fabricate percentages." if ui_config.get("data_privacy") else "Keep exact figures from the FactSheet."}
5. Preserve direct quotes and section structure (## headings).
6. Do NOT add a References section — it will be appended separately.

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

    # --- Deterministic hallucination scrub (runs regardless of LLM behaviour) ---
    edited = _scrub_hallucinations(edited, fact_sheet)
    edited = _remove_empty_exhibits(edited)

    refs = _build_references(
        master_transcript,
        fact_sheet,
        ui_config.get("citation", "APA (7th Edition)"),
        company,
    )

    if "## References" not in edited:
        edited = edited.rstrip() + refs

    return _strip_em_dashes(edited)
