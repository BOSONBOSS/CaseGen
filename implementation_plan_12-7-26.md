# Universal Case Study Quality & Context Upgrades

This plan details the universal improvements required to fix the factual context, causal logic, and narrative depth issues identified in the comparative analysis (Case #20 vs Case #13). Crucially, these changes are designed to act dynamically with any dataset and strictly respect all user-selected UI configurations.

## User Review Required

Please review the architectural philosophy and the phased rollout plan below. We will implement these in three distinct phases to isolate data integrity changes from narrative styling changes, minimizing the risk of prompt regressions, and capping it off with architectural stability.

---

## Architectural Philosophy: How We Handle UI Configurations

**"How much hand-holding does a frontier LLM actually need?"**
- **Semantic Styling (No backend mapping needed):** For UI options like Tone, Audience, Theme, and Discipline, the LLM can handle it entirely on its own. We will inject the exact strings from the UI (e.g., "Discipline: Finance", "Tone: Highly Critical") directly into the context. The LLM's vast latent knowledge will naturally adapt the vocabulary, frameworks, and focus without us needing to hardcode definitions.
- **Mechanical/Functional Rules (Requires explicit backend logic):** For strict actions (Data Privacy, Structural Exactness, Citation formats), the LLM's natural urge to write fluid prose will override simple labels. We must map these UI toggles to strict, shouted rules in the prompt architecture (e.g., *"IF Privacy=True THEN you MUST replace all exact financial figures..."*).

---

## Proposed Changes (Phased Rollout)

### Phase 1: Data Integrity & Exhibit Richness
*We will implement this phase first. Focus: Ensuring Agent 1 extracts perfect data and Agent 3 builds accurate, rich, privacy-compliant tables before the narrative is even written.*

1. **The "Copy-Paste" Rule (Agent 1):** Add a strict rule that numerical extractions from tables/spreadsheets must be exact, character-for-character copies of the source cells, forbidding rounding or approximation (e.g., extracting exactly 10,823,000, not 10.59M).
2. **Metadata Inheritance & Privacy (Agent 3 - Exhibits):** 
   - Instruct Agent 3 that if a raw fact contains a temporal qualifier (e.g., "Q1", "Jan-May", "YTD", "Cumulative"), that qualifier **MUST** be explicitly copied into the "Context" or "Note" column of the generated table.
   - **Mechanical Rule:** If `Data Privacy = True` in the UI config, Agent 3 MUST replace exact numbers in the tables with directional bands (e.g., "> 10 Million units").
3. **Multi-Table Generation (Agent 3 - Exhibits):** Update Agent 3 to generate *multiple* focused tables rather than one mega-table. If it detects time-series data, it should spawn a "Trend Analysis" exhibit. If categorical, a "Segment Breakdown" exhibit. (If `Purpose = Executive Summary`, it will keep tables brief).

### Phase 2: Narrative Arc & Causal Logic
*Implemented after Phase 1 is verified. Focus: Upgrading Agent 2 to write sharp, argumentative, and evidence-backed prose that dynamically respects the UI semantics.*

1. **Dynamic, Non-Generic Thesis Generation (Agent 2):**
   - **Mechanical Rule:** The Anti-Meta Rule. Ban phrases like "This case study will explore...". 
   - **Semantic Injection:** Mandate a sharp, argumentative thesis in the Background section that explicitly matches the selected `{Tone}` and `{Purpose}`. (e.g., an Investor Memo with a Critical tone gets a financially aggressive thesis).
2. **Causal Evidence Mandate (Agent 2):**
   - **Mechanical Rule:** In the Results section, forbid the LLM from stating that an intervention *caused* an outcome unless it provides the mechanism.
   - **Semantic Injection:** The complexity of this causal explanation will naturally adapt to the `{Audience}` UI setting.
3. **Company-Specific Learning Outcomes (Agent 2):**
   - **Mechanical Rule:** The Platitude Ban. Explicitly reject generic adages (e.g., "Customer engagement is important"). Mandate that at least 3 out of 5 outcomes specifically reference a proprietary framework or unique strategic initiative from the text.
   - **Semantic Injection:** The takeaways will naturally align with the `{Discipline}` chosen in the UI.

### Phase 3: Stability & Optimization (App Architecture)
*Implemented last. Focus: Preventing edge-case crashes and API exhaustion in the Streamlit UI.*

1. **Fix History Load Crash (`pages/5_Edit_Export.py`):**
   - **Bug:** Loading a case from `My Case Studies` currently crashes when the app tries to generate the PDF filename (KeyError on `filtered_fact_sheet`).
   - **Fix:** Wrap the filename generator in a `.get()` fallback to gracefully handle historical markdown loads where session state is incomplete.
2. **Prevent Token/Rate-Limit Exhaustion (`pages/1_Upload_Documents.py`):**
   - **Bug:** There is no hard cap on input size. A massive upload (e.g. 5M+ characters) will spawn thousands of chunks, leading to catastrophic 429 API errors, UI freezes, and huge costs.
   - **Fix:** Add a strict character limit check (e.g., max 1 million characters) on Page 1 before proceeding to generation.
3. **Graceful Pydantic Failure (`pipeline/agents/llm_client.py`):**
   - **Bug:** If the LLM completely hallucinates a JSON structure (e.g., returning a List instead of a Dict), `generate_validated_json` exhausts retries and halts the app abruptly with an unhandled stack trace.
   - **Fix:** Wrap `run_agent_1` in a try/except that yields an empty/default `FactSheet` or gracefully alerts the user instead of throwing a fatal red-screen error.

---

## Verification Plan

### Phase 1 Verification
- Run a generation on the Toyota Sales Performance dataset.
- **Verify Agent 1:** Ensure exact sales figures are extracted without rounding.
- **Verify Agent 3:** Ensure tables preserve temporal context ("Jan-May 2026"), spawn multiple focused exhibits, and successfully mask numbers when Data Privacy is toggled ON.

### Phase 2 Verification
- **Verify Agent 2:** Ensure the Background section opens with a sharp thesis (no meta-commentary), the Results section contains explicit causal linkages, and the Learnings are Toyota-specific (e.g., referencing *genchi genbutsu* rather than generic principles).

### Phase 3 Verification
- Go to Page 6, load a saved case study, and verify Page 5 renders and allows PDF export without a KeyError.
- Mock a massive file upload and verify Page 1 displays a warning and stops execution before exhausting tokens.
