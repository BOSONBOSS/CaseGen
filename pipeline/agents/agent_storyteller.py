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

GENTLE NARRATIVE GUIDELINES (CRITICAL):
1. Anti-Wordiness: Write concisely and directly. Do NOT use generic filler phrases like "This initiative was designed to..." or "What made this distinctive was...". Start sentences directly with the subject or action.
2. Thesis (Background section): Ensure the introduction establishes a clear tension (e.g., a strategic challenge) and an arguable thesis, not just a list of facts.
3. Subheadings (Intervention section): Use descriptive markdown subheadings (###) to clearly organize and separate distinct interventions or strategic initiatives.
4. Causal Mechanisms (Results section): When describing outcomes, explicitly explain the specific mechanism of HOW the intervention led to the result (don't just state the correlation).
5. Synthesis (Learnings section): Conclude with a final synthesis paragraph that reconnects to the opening thesis, placed immediately before any discussion questions.
6. Quote Integrity: The opening quote MUST be taken verbatim from the key_quotes field in the FactSheet. Do NOT paraphrase, adapt, or invent any quote.

Template sections (minimum word targets — there is NO maximum; write as much as the data warrants):
{sections_block}

Few-shot examples (mimic tone and structure exactly):
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

    # ── Section-specific narrative architecture rules ──────────────────────────
    narrative_rules = {
        "background": f"""
NARRATIVE ARCHITECTURE — COMPANY BACKGROUND:
Purpose of this case study: {ui_config.get('purpose', 'General')} | Tone required: {ui_config.get('tone', 'Neutral')} | Audience: {ui_config.get('audience', 'General')}

Your job is to open the entire case study with a powerful, memorable hook. This is the first thing
the reader sees; it must immediately establish the dramatic stakes.

  a) HOOK (first paragraph): Open with the single most compelling fact, quote, or moment from
     the FactSheet — a striking statistic, a CEO's bold declaration, or a pivotal event. DO NOT
     open with a boring "Company X was founded in year Y" sentence. The hook must create
     intellectual tension: why does this company matter RIGHT NOW?

  b) THESIS STATEMENT (CRITICAL): In the second paragraph, state the central argument of this
     entire case study in 1-2 sentences. This thesis MUST be:
     - Specific and arguable, not generic
     - Calibrated to the Tone above (e.g. if Tone is 'Critical', the thesis should interrogate
       the strategy; if 'Analytical', it should frame a testable hypothesis)
     - Calibrated to the Purpose above (e.g. if Purpose is 'Investor Memo', the thesis frames
       financial risk/opportunity; if 'Teaching Case', it frames the core management dilemma)
     EXAMPLE OF A STRONG THESIS: "Toyota's multi-pathway strategy spanning BEVs, FCEVs, and HEVs
     reflects a conviction that no single technology can serve all markets equally — a bet that
     sets it apart from every major competitor, but one whose long-term viability depends on
     whether governments and consumers align with Toyota's timeline."
     EXAMPLE OF A WEAK THESIS (BANNED): "Toyota faces challenges in a changing market."
     The thesis must be woven as a recurring theme that every subsequent section refers back to.

  c) ANTI-META BAN (CRITICAL): NEVER use the following phrases or anything like them:
     - Opening meta: "This case study will explore...", "In this report, we will...", "As we will see...",
       "This paper examines...", "The following sections detail...", "We will analyze..."
     - Closing clichés: "In summary,", "To summarize,", "In conclusion,", "To conclude,",
       "Overall,", "In essence,", "Taken together,"
     These are formulaic crutches. A great case study SHOWS its argument — it never announces or
     summarises it. Let the evidence and narrative speak for themselves. If you need a transition,
     use substantive connectives: "Consequently,", "This translated into...", "The result was...",
     "What followed was...", "This decision proved pivotal because...".

  d) COMPANY PORTRAIT: After the hook and thesis, provide a rich portrait of the company —
     its founding, scale, culture, and strategic identity — using ONLY data from the FactSheet.
     Integrate all key_people, timeline_events, and strategic_initiatives mentioned.

  e) DO NOT use a generic "founded in X" opening line. The hook comes first.
""",

        "industry_context": """
NARRATIVE ARCHITECTURE — INDUSTRY CONTEXT:
This section must explain WHY the challenge the company faces is real, urgent, and consequential.
It should read like the backdrop to a film — establishing the forces at play BEFORE the protagonist
acts. Specifically:

  a) MACRO FORCES: Describe the large-scale industry shifts (regulatory, technological, consumer)
     using data from the FactSheet. Connect each force directly to the company's situation.
     Do not list trends abstractly — explain how each trend creates pressure on THIS company.

  b) COMPETITIVE DYNAMICS: Explain the competitive landscape using ONLY entities named in the
     FactSheet. Do not invent competitor names. If no competitors are named, describe the
     competitive pressure qualitatively ("established global automakers", "domestic rivals").

  c) STRATEGIC IMPERATIVE: End this section with a clear statement of why the status quo is
     not sustainable — what happens if the company does nothing? This builds urgency for the
     Challenge section that follows.
""",

        "challenge": """
NARRATIVE ARCHITECTURE — THE CHALLENGE:
This is the heart of the case. Write it as a multi-layered problem that has DEPTH, not just breadth.
Think of this section as a diagnosis: by the end, the reader must understand exactly WHY the
challenge exists and what is at stake.

  a) PROBLEM STATEMENT: Open with a crisp, one-paragraph statement of the core challenge.
     Make it specific — include numbers, regions, timeframes from the FactSheet.

  b) ROOT CAUSES: Go beneath the surface symptom to explain the structural reasons for the
     challenge. For example, if sales declined in China, WHY? What are the underlying forces
     (consumer shifts, local competitors, pricing, infrastructure)?

  c) TENSION AND STAKES: Make the reader feel the difficulty of the decision. What makes this
     challenge hard? What are the competing pressures and trade-offs the company faces?
     Use the FactSheet's language and data to make this feel concrete, not abstract.

  d) CHRONOLOGY: Show how the challenge developed over time using timeline_events. Do NOT
     present historical events (decades-old) as current crises. Frame historical context as
     "the foundation on which today's challenge rests."
""",

        "intervention": """
NARRATIVE ARCHITECTURE — INTERVENTION / APPROACH:
This is the longest and most analytical section. Write it as a strategic story: WHO decided WHAT,
WHY that specific approach was chosen, and HOW it was executed.

  a) STRATEGIC LOGIC: Before describing WHAT was done, explain WHY this approach was chosen
     over alternatives. What is the underlying strategic logic? This is the "why it's brilliant"
     paragraph that transforms a list of actions into a coherent strategy.

  b) NAMED PROTAGONISTS: Every major initiative must be attributed to a named decision-maker
     from the FactSheet's key_people. Do not write "the company decided" — use the actual
     name and title from key_people (e.g. "[CEO Name] directed..." or "[Chairman Name] championed...").
     If no named individual is in the FactSheet for a decision, attribute it to the specific team or function.

  c) INITIATIVE DEEP-DIVES: For each strategic initiative (especially those in
     strategic_initiatives), write a dedicated sub-section that explains:
     - What it is (name it precisely as it appears in the FactSheet)
     - What problem it solves
     - How it works (mechanism, not just description)
     - What makes it distinctive or innovative
     - Key partnerships or collaborations involved (name all partners from key_partnerships)

  d) CAUSAL EVIDENCE MANDATE (CRITICAL): At the end of EACH initiative description, you MUST
     explicitly state the causal mechanism linking that initiative to its outcome. The structure
     MUST follow this logic: "By doing [X], the company achieved [Y] BECAUSE [Z mechanism]."
     BANNED: "This initiative improved results." (no mechanism)
     BANNED: "The strategy led to growth." (no specifics)
     REQUIRED FORMAT: "By [specific action taken], [Company] achieved [specific measurable outcome]
     because [mechanism — i.e. how and why this action produced this specific result]."
     If the FactSheet does NOT provide a causal link between an initiative and an outcome,
     state the initiative and its intended goal separately. DO NOT invent causation.
""",

        "results": """
NARRATIVE ARCHITECTURE — RESULTS & IMPACT:
Show don't tell. This section must be data-dense and analytically rich.

  a) QUANTITATIVE WINS: Lead with the hardest, most specific numbers from raw_facts and
     outcomes. Use before-vs-after structure where the FactSheet provides it. Every result
     MUST include the year or time period it belongs to.

  b) CAUSAL ATTRIBUTION (CRITICAL): Do NOT list outcomes in isolation. For EVERY result,
     you MUST answer "why did this happen?" using this structure:
     "[Outcome] happened because [specific intervention or mechanism] which worked by [how]."
     BANNED: "Sales grew 12% in 2024." (no cause)
     BANNED: "The company saw improved profitability." (no mechanism)
     REQUIRED FORMAT: "[Specific metric] reached [exact figure] in [year], a [X%] increase,
     driven by [named initiative] which worked by [mechanism — why this produced that result]."
     If the FactSheet does not explain WHY an outcome occurred, present the result with its
     number and year, then note the strategic action that preceded it — without inventing
     a causal link that is not in the data.

  c) BROADER IMPACT: Address impact on multiple stakeholders — customers, employees,
     investors, communities, environment — using only FactSheet data.

  d) HONEST ASSESSMENT: If the FactSheet contains any challenges, setbacks, or unresolved
     issues alongside the wins, include them. A credible case study acknowledges complexity.
     Do not write a pure success story if the data shows nuance.
""",

        "learnings": f"""
NARRATIVE ARCHITECTURE — LEARNING OUTCOMES:
Discipline: {ui_config.get('discipline', 'General Business')} | Audience: {ui_config.get('audience', 'General')}

This section must deliver SPECIFIC, ACTIONABLE, COMPANY-SPECIFIC insights — not generic
management platitudes that could apply to any company in any industry.

  a) PLATITUDE BAN (CRITICAL): The following generic statements (and anything like them) are
     STRICTLY FORBIDDEN in this section:
     - "Adaptability is key."
     - "Customer engagement is important."
     - "Innovation drives success."
     - "Leadership matters."
     - "Companies must embrace change."
     - "Sustainability is a priority."
     If you write any of these, you have FAILED. Every single learning outcome MUST be anchored
     to a named initiative, a specific number, or a proprietary framework from the FactSheet.
     At least 3 out of your learning outcomes MUST reference something unique to this company
     (a named programme, a specific metric, a proprietary process, or a named decision-maker).

  b) COMPANY-SPECIFIC PRINCIPLES: Every learning outcome must be grounded in something
     SPECIFIC to this company's experience. Instead of "adaptability is important," write:
     "[Company]'s [specific named initiative] demonstrates that [specific mechanism] creates
     [specific advantage] — a lesson applicable to any company facing [specific condition]."

  c) CAUSAL EXPLANATIONS: Each learning must explain the mechanism — not just WHAT happened
     but HOW and WHY it worked. Connect each lesson back to the specific interventions and
     results from previous sections.

  d) TRANSFERABLE FRAMEWORK: After the company-specific insights, distil 2-3 principles that
     managers in OTHER industries could apply, explicitly stating what conditions make each
     principle applicable.

  e) OPEN TENSIONS: End with 1-2 unresolved questions that the case raises but does not answer.
     These should feel genuinely difficult — two legitimate strategic paths that the data does
     not definitively resolve. Make them company-specific, not generic.

  f) DISCUSSION QUESTIONS: Include 4-6 substantive, open-ended discussion questions calibrated
     to the Discipline and Audience above. Questions should be of two types:
     TYPE A (Framework-grounded): Apply a named analytical framework to a specific data point
       from the FactSheet. Choose frameworks relevant to the Discipline (e.g. Porter's Five
       Forces, PESTLE, Resource-Based View, SWOT, Blue Ocean Strategy, BCG Matrix, Balanced
       Scorecard, Triple Bottom Line, Lean/TPS, PDCA, ISO standards for quality, etc.).
       Example: "Using the Resource-Based View, assess whether [Company]'s [named initiative]
       constitutes an inimitable resource that competitors cannot replicate within 5 years."
     TYPE B (Open / Reflective): Pose a genuine strategic dilemma or ethical question that
       invites discussion without a single right answer. These should be rooted in the specific
       facts and tensions in the case, not generic.
       Example: "If you were [CEO Name], would you [strategic path A] at the risk of [downside A],
       or pursue [strategic path B] given [evidence from FactSheet]?"
     Include at least 2 of each type. All questions must be specific to this company's situation.
     BANNED: "How did the company manage change?" or "What can other companies learn from this?"
""",
    }

    narrative_rule = narrative_rules.get(section_id, "")

    return f"""
You are a Harvard Business School-calibre case study author. Generate ONLY the "{section_id}" section ({section.get("title", section_id)}).

{enumeration_block}
{narrative_rule}

═══════════════════════════════════════════════════════════
DATA INTEGRITY RULES (non-negotiable — enforced post-hoc by a code scrubber):
═══════════════════════════════════════════════════════════
1. Do NOT invent operational details (e.g., "brainstorming sessions", "workshops",
   "restructured workforce", "marketing campaigns", "budget allocated") unless explicitly
   stated in the FactSheet. Respect the chronological timeline: historical facts are history,
   not current crises.
2. Do NOT invent narrative drama or emotions ("struggling", "under pressure", "lagging",
   "fraught with challenges") unless those exact words appear in the FactSheet. If the
   FactSheet describes a proactive, confident strategy, present it as confident and deliberate.
3. Do NOT draw unsupported cautionary conclusions. Stick strictly to the tone in the source.
4. Use ONLY named entities (people, products, partners, awards, programmes) that explicitly
   appear in the FactSheet. Describe anything absent generically.
5. REVENUE / MARKET SIZE RULE: If the FactSheet does not explicitly state a total revenue or
   market size figure, you MUST NOT invent one. SPECIFICALLY: NEVER write any currency+large-unit
   figure (e.g. '¥30 trillion', '$500 billion') unless it appears verbatim in the FactSheet's
   revenue or raw_facts fields. If revenue is null in the FactSheet, describe scale qualitatively
   (e.g. "one of the world's largest companies in its sector by revenue").
5b. PARTIAL-YEAR DATA RULE: If a raw_fact is labelled as "Jan-May", "cumulative", "YTD", or
   "partial year", you MUST cite it with that qualifier (e.g. "In the first five months of [year],
   [Company] recorded [figure]"). NEVER present a partial-year figure as if it is a
   full annual total, and NEVER extrapolate or annualise a partial figure to estimate a full year.
6. METRICS CLAIM RULE: NEVER write "specific quantitative metrics were not disclosed" or
   "no figures were available." If there is truly no data, simply omit that topic entirely.

7. QUOTE VERBATIM RULE: Copy quotes CHARACTER-FOR-CHARACTER from key_quotes. Do NOT
   paraphrase, condense, or add words. If no exact match exists, write the point as prose.

═══════════════════════════════════════════════════════════
TONE AND VOICE RULES:
═══════════════════════════════════════════════════════════
8.  Use ACTIVE VOICE throughout. "[Company] launched [Initiative]" not "[Initiative] was launched."
9.  Match the STRATEGIC CONFIDENCE of the source document. This company has a plan.
10. Use EXACT TERMINOLOGY from the FactSheet — proprietary framework names, programme titles,
    strategic labels, brand names — never paraphrase into generic terms.
11. INDUSTRY-SPECIFIC TERMINOLOGY: Use the precise technical vocabulary from the FactSheet.
    If this is an automotive company, use exact powertrain terms (BEV, PHEV, HEV, FCEV) — never
    the generic "EV." If this is a pharma company, use exact drug/trial terminology. If this
    is a tech company, use exact product/platform names. Always prefer the FactSheet's own language.
12. CRITICAL DATA RULE: Every paragraph MUST contain at least one specific number, percentage,
    date, or quantitative metric from the FactSheet. NEVER write a paragraph of purely qualitative
    prose when numbers are available. If the FactSheet has 10 numbers, use all 10 in the text.
    Do NOT save numbers only for exhibits — weave them directly into sentences.
13. NAMED INITIATIVES RULE: strategic_initiatives in the FactSheet are named programmes —
    write substantively about each. key_partnerships are named external partners — name them.
14. EM-DASH BAN: Do NOT use em-dashes (—) anywhere in your output. Use a comma, a colon,
    or a new sentence instead. This is a hard formatting rule.

{exhibit_ref_rule}

═══════════════════════════════════════════════════════════
LENGTH RULE: Write between {section.get("word_count_min", 400)} and {section.get("word_count_max", 2000)} words. A rich, detailed section that fully uses all FactSheet data is always better than a short one, but do NOT pad the text with repetitive fluff just to reach the maximum limit.
═══════════════════════════════════════════════════════════

{ctx}

Return ONLY raw markdown text. Do NOT wrap it in a JSON object. Just write the prose directly.
Do NOT include the section heading (e.g. "## {section.get("title", section_id)}") at the top of your text; it will be added automatically.

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
        from pipeline.agents.llm_client import generate_text
        result = generate_text(prompt)
        narrative[section_id] = result
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
    from pipeline.agents.llm_client import generate_text
    result = generate_text(prompt)
    updated = dict(existing_narrative)
    updated[section_id] = result
    return updated
