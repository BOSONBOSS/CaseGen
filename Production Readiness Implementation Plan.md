# CaseGen — Production Readiness Implementation Plan

## Goal
Bring the CaseGen pipeline from **strong prototype (B-)** to **production-ready tool (B+ / A- consistently)**, ready for handover. The target is 5 consecutive case studies from different companies and topics all scoring B+ (83%+) or above without manual prompt debugging.

---

## Architecture Overview (Current State)

```
[User Uploads Docs] → [Agent 1: Extractor] → FactSheet JSON
                                                    ↓
                            [Agent 3: Analyst] → Exhibits + Discussion Qs
                                                    ↓
                            [Agent 2: Storyteller] → Narrative sections
                                                    ↓
                            [Agent 4: Editor] → Final polished Markdown
                                                    ↓
                            [Export] → Word (.docx) / PDF
```

**UI:** 5-page Streamlit app (`Home.py` + `pages/1–6`).  
**Section regeneration already exists** in `5_Edit_Export.py` — individual section buttons are already built.  
**Key gap:** No quality gate between Agent 4 output and the export buttons.

---

## What Will NOT Be Changed

The following are working correctly and will not be touched:
- Export pipeline (`markdown_to_docx.py`, `markdown_to_pdf.py`)
- Section regeneration buttons (already built in `5_Edit_Export.py`)
- Agent 4 (Editor) — functioning well
- Agent 1 (Extractor) — recent quote verbatim fix is in; no further changes needed
- UI layout and navigation flow

---

## Phase 1 — Automated Quality Validator
**Effort: ~3 days | Impact: 🔴 Eliminates ~60% of recurring errors**  
**Risk: Zero** — read-only; does not touch generation code

### What it is

A new lightweight Python module `pipeline/agents/agent_validator.py` that receives the completed `final_markdown` string and the `filtered_fact_sheet` and outputs a structured list of flags **before** the export buttons appear.

### What it checks

| Check | How it detects it |
|---|---|
| **Empty exhibit** | Regex: finds `**Exhibit N:` header followed immediately by `**Exhibit` or end-of-string with no table rows |
| **Invented number** | For each number in exhibits, checks if that exact digit string appears anywhere in `raw_facts` JSON. If not → flag as "unverified figure" |
| **Partial-year vs full-year YoY** | Regex: finds any percentage (e.g. `-3.53%`) in the same row as "Jan–May" or "Q1" or "YTD" alongside a full-year column (e.g. "2023") |
| **Fabricated / paraphrased opening quote** | Extracts the opening block-quoted text and checks if it appears verbatim in `key_quotes` from the FactSheet |
| **Anti-meta phrases** | Scans for a banned phrase list: "this case study will", "in this report, we", "as we will see", "this report explores" |
| **Temporal causation** | Soft check: if a `strategic_initiative` has a `year` and the narrative paragraph preceding a percentage claim mentions that initiative, flag it for human review |

### What it outputs

A Python list of `ValidationFlag` objects:

```python
@dataclass
class ValidationFlag:
    severity: str        # "CRITICAL", "WARNING", "INFO"
    check_name: str      # e.g. "EMPTY_EXHIBIT"
    description: str     # human-readable message
    location: str        # e.g. "Exhibit 4", "Background section"
    auto_fixable: bool   # True if the system can re-run to fix it
```

### Where it plugs into the UI

In `5_Edit_Export.py`, **after** Agent 4 runs and produces `final_markdown`, call the validator **before** rendering the download buttons. Show a collapsible "Quality Report" panel above the text editor:

```
┌─────────────────────────────────────────────────┐
│  Quality Report                          [▼]    │
│  🔴 CRITICAL (1):  Empty Exhibit 4              │
│  ⚠️  WARNING (2):  Unverified figure "5,000,000" │
│                   Partial YoY comparison        │
│  ✅ PASS (4): Anti-Meta, Quote, Schema, Period  │
└─────────────────────────────────────────────────┘
[Download Word]  [Download PDF]   ← Still visible; user decides
```

> [!IMPORTANT]
> The validator **does not block export**. It informs the user. The user decides whether to regenerate a section or export anyway. This is intentional — we don't want to lock a user out of their work.

### Files to create / modify

| Action | File |
|---|---|
| **[NEW]** | `pipeline/agents/agent_validator.py` |
| **[MODIFY]** | `pages/5_Edit_Export.py` — add validator call and Quality Report panel |

### How to test Phase 1

1. **Unit test the validator directly** — run it against the saved markdown for case studies #33, #34, #35 (known bad cases). Verify it catches:
   - The empty Exhibit 4 from #35 → should flag `CRITICAL: EMPTY_EXHIBIT`
   - The 5,000,000 figure from #35 → should flag `CRITICAL: UNVERIFIED_FIGURE`
   - The -3.53% partial-year YoY from #35 → should flag `CRITICAL: PARTIAL_YEAR_YOY`
   - The paraphrased Koji Sato quote from #35 → should flag `CRITICAL: QUOTE_NOT_IN_FACTSHEET`

2. **Run it against a good case study** (#13 or #28) — verify it produces **zero CRITICAL flags**.

3. **Manual UI test** — generate a new case study and confirm the Quality Report panel appears, is readable, and the download buttons are still accessible regardless of flags.

**Pass criteria:** All 4 known errors in #35 are caught. Zero false positives on #13 or #28.

---

## Phase 2 — Prompt Stabilisation: Causal Logic
**Effort: ~1 day | Impact: 🟡 Fixes the most persistent weakness**  
**Risk: Low** — adds examples, does not remove existing rules

### What it is

The Causal Evidence Mandate in `agent_storyteller.py` currently has rules and a banned-phrase list. The problem is that the LLM has "rule fatigue" — too many abstract `CRITICAL` instructions. The fix is adding **2 concrete few-shot examples** directly into the prompt: one showing a correctly written causal paragraph, one showing a banned one.

### What it adds to the prompt

Immediately after the existing `CAUSAL EVIDENCE MANDATE` block in the `intervention` section:

```
FEW-SHOT EXAMPLES FOR CAUSAL WRITING:

✅ CORRECT EXAMPLE:
"Lexus sales grew from 824,258 in 2023 to 882,231 in 2025, driven by a deliberate 
product expansion strategy that introduced BEV models into the Lexus lineup for the 
first time, directly addressing demand from premium-segment consumers who had previously 
had no Toyota Group BEV option at the luxury tier. Woven City — which launched in 
September 2025 — did not drive this growth; it is positioned as a future innovation 
platform to sustain this trajectory from 2026 onward."

❌ BANNED EXAMPLE (DO NOT WRITE LIKE THIS):
"Woven City has contributed to the growth of Lexus sales. The initiative has enhanced 
Toyota's innovation reputation, leading to increased consumer confidence and higher 
purchase intent across the Lexus range."
Why it is banned: Woven City launched after the sales growth occurred. The mechanism 
is vague ("enhanced reputation"). No specific data links the initiative to the outcome.
```

### Files to modify

| Action | File |
|---|---|
| **[MODIFY]** | `pipeline/agents/agent_storyteller.py` — add few-shot examples to intervention prompt |

### How to test Phase 2

Generate a new case study on a different company and topic. In the output, locate every paragraph in the Intervention section that makes a causal claim.

Check each one manually against this rubric:
- Does it name a specific initiative?
- Does it state a specific, dated outcome?
- Does it explain the mechanism (why the initiative caused the outcome)?
- Is the initiative's launch year **before** the outcome's year?

**Pass criteria:** All causal paragraphs in the Intervention section pass all 4 checks. Zero temporal inversions. The Phase 1 validator should also show zero CRITICAL flags for causal issues.

---

## Phase 3 — Thesis Pre-Generation Step
**Effort: ~1 day | Impact: 🟡 Consistent B+ theses**  
**Risk: Low** — adds a step before the Background section, does not change other sections

### What it is

Currently, the Storyteller writes the Background section in one shot and produces whatever thesis it thinks fits. The thesis is consistently descriptive rather than argumentative.

The fix is a **"think before you write" step** — before Agent 2 starts writing the Background, a short pre-prompt generates **only the thesis sentence**, evaluates it against criteria, and passes it as a constraint into the Background generation.

### How it works

In `agent_storyteller.py`, before generating the `background` section, call a small additional LLM call:

```
THESIS PRE-GENERATION PROMPT:
Given this FactSheet, write ONE thesis sentence for this case study.
The sentence MUST:
1. Make an ARGUABLE CLAIM (not a fact) about the company's strategy
2. Name a specific tension or risk (e.g. "while X, it faces Y")
3. Be specific to THIS company, not generic

Output ONLY the thesis sentence. Nothing else.

BANNED THESIS PATTERNS:
- "[Company] has demonstrated commitment to [value]" — too generic
- "[Company] achieved [metric] in [year]" — this is a fact, not a claim
- "[Company]'s approach to [topic] shows [vague quality]" — no tension

GOOD THESIS PATTERN:
"[Company]'s [specific strategy] positions it to [specific opportunity], 
but risks [specific threat] if [specific condition] is not met."
```

The returned thesis sentence is then injected as a `required_thesis` variable into the Background section prompt, with the instruction: "Your Background section MUST open with or build toward this thesis."

### Files to modify

| Action | File |
|---|---|
| **[MODIFY]** | `pipeline/agents/agent_storyteller.py` — add `_generate_thesis()` function and wire it into the background section call |

### How to test Phase 3

Generate 3 case studies on different topics. Extract the opening paragraph of each Background section.

Check each thesis against the criteria:
- Is it a claim (not a fact)?
- Does it name a specific tension or risk?
- Could it only describe THIS company (not any company)?

**Pass criteria:** All 3 theses pass all 3 checks. None should read as a generic "commitment to innovation" statement. Estimated uplift from ~65% to ~80%+ on Thesis Quality score.

---

## Phase 4 — Named Sub-Entity Extraction Rule
**Effort: ~2 hours | Impact: 🟢 Fixes recurring Daihatsu/Hino missing data**  
**Risk: Very low** — a single targeted addition to the Extractor

### What it is

The Extractor's Volume Control rule tells it to prioritise "top-level worldwide totals" and "skip minor country-level data." Daihatsu and Hino are Toyota Group sub-entities, not countries — but the Extractor incorrectly treats them as minor detail and drops them.

The fix is one line added to the existing extraction prompt:

```
TOYOTA GROUP ENTITY RULE: If the source document is from Toyota Motor Corporation, 
the following sub-entities are NEVER minor detail and MUST always be extracted 
into raw_facts whenever data exists for them:
- Toyota + Lexus (combined brand)
- Lexus (standalone brand)
- Daihatsu Motor Co.
- Hino Motors Ltd.
- Total Group (all brands combined, including Daihatsu and Hino)
These five are strategic data points, not peripheral sub-segments. Treat them with 
the same priority as the worldwide total figure.
```

> [!NOTE]
> This rule is Toyota-specific. For other companies, the principle remains — named subsidiaries with their own brand identity should never be dropped. A future generalisation could extract the list of named subsidiaries dynamically from the source documents.

### Files to modify

| Action | File |
|---|---|
| **[MODIFY]** | `pipeline/agents/agent_extractor.py` — add Toyota Group Entity Rule to the extraction prompt |

### How to test Phase 4

Run a Toyota case study. Open the saved FactSheet JSON (visible in the app or from `output/` directory). Verify `raw_facts` contains explicit entries for:
- Toyota + Lexus total
- Lexus standalone
- Daihatsu
- Hino
- Total Group

**Pass criteria:** All 5 entity rows appear in `raw_facts`. The Analyst's Exhibit 2 (Sales & Product Breakdown) then shows all 5 as separate rows.

---

## Phase 5 — Validation Run (5 Consecutive B+ Studies)
**Effort: Depends on API access | Impact: Confirms tool is stable**

This is not a development phase — it is a **quality certification run**.

### Protocol

1. Generate 5 case studies using different companies and different themes:
   - A US automotive company (different from Toyota)
   - A consumer goods company
   - A tech company
   - A financial services company
   - A healthcare company

2. For each generated case study, run it through the same review rubric used for #28–#35:
   - Factual Accuracy (25%)
   - Phase 1 Data (15%)
   - Phase 1 Exhibits (10%)
   - Phase 2 Anti-Meta (10%)
   - Phase 2 Thesis (10%)
   - Phase 2 Causal (15%)
   - Phase 2 Learnings (10%)
   - Narrative Quality (5%)

3. Record the grade. If any case study scores below B+ (83%):
   - Identify which check it failed
   - Determine if it is a prompt issue, a data issue, or a new failure mode
   - Fix and re-run **only that case study** before proceeding

### Pass criteria

**5 consecutive case studies, 5 different companies/topics, all scoring B+ (83%+).** At this point the tool is stable and ready for handover.

---

## Summary — Phased Rollout

```
Phase 1: Automated Validator    (~3 days)   Read-only safety net
    ↓
Phase 2: Causal Few-Shot        (~1 day)    Fixes worst narrative weakness
    ↓
Phase 3: Thesis Pre-Generation  (~1 day)    Consistent argumentative openings
    ↓
Phase 4: Sub-Entity Rule        (~2 hours)  Fixes Daihatsu/Hino data gap
    ↓
Phase 5: 5× Validation Run      (ongoing)   Certification that tool is stable
```

**Total estimated effort: ~6.5 days of development + validation runs.**

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 2/3 prompt changes introduce new failure modes | Low | Test immediately against #13 (gold standard) — if #13 degrades, revert |
| Validator produces false positives on good case studies | Medium | Test against #13 and #28 before shipping; tune regex patterns |
| 5-run validation exposes new company-specific failure | Medium | Expected; fix and continue. The protocol allows targeted fixes mid-run |
| API token costs increase due to thesis pre-generation step | Low | The thesis pre-call is ~200 tokens — negligible vs. the full narrative cost |

---

## Definition of "Done"

The tool is production-ready when:

- [ ] Phase 1: Validator runs on every generated case study and Quality Report is visible in the UI
- [ ] Phase 2: Zero temporal causation errors across 3 consecutive test runs
- [ ] Phase 3: Zero "commitment to innovation"-style generic theses across 3 consecutive test runs
- [ ] Phase 4: All Toyota Group sub-entities appear in FactSheet `raw_facts` on every Toyota run
- [ ] Phase 5: 5 consecutive case studies, 5 companies, all score B+ (83%+)
