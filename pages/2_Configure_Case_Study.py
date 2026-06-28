import streamlit as st
import time

from pipeline.ingest.merge_sources import total_char_count
from config import CHUNK_SIZE, CHUNK_OVERLAP

st.set_page_config(
    page_title="Configure Case Study | CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    .block-container { padding-top: 2.5rem !important; max-width: 900px; }

    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #E2E8F0;
    }

    .page-title {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 26px;
        font-weight: 400;
        color: #0F172A;
        margin-bottom: 0.4rem;
    }
    .page-desc {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    .section-label {
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #2563EB;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="padding:0.25rem 0 0.75rem;">
    <div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
    <div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("**Step 2 of 5** — Configure")
st.sidebar.caption("Set the scope, tone, and audience before the AI pipeline begins.")

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Configure Your Case Study</div>', unsafe_allow_html=True)
st.markdown('<div class="page-desc">These settings control how the AI writes your case study. Every choice here is routed to the correct agent.</div>', unsafe_allow_html=True)

# ── Guard: warn if no transcript uploaded ─────────────────────────────────────
_transcript = st.session_state.get("master_transcript")
if not _transcript or total_char_count(_transcript) < 500:
    st.warning("No documents have been uploaded yet. Go back to Page 1 and upload your source files first.")

# ── Configuration Form ────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown('<div class="section-label">Core Settings</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        purpose = st.selectbox(
            "Output Purpose",
            [
                "IFQM Teaching Case (Standard academic format)",
                "Corporate Post-Mortem (Internal lessons learnt report)",
                "Investor Memo (Financial and risk heavy brief)",
                "B2B Marketing Story (Success story for client)",
                "Executive Summary (Short, bullet point heavy)",
            ],
            help="Determines the overall structure and depth of the case study."
        )

        discipline = st.selectbox(
            "Business Discipline",
            [
                "Strategy",
                "Operations",
                "HR",
                "Brand and marketing",
                "Supply chain",
                "Quality management",
                "Finance and Accounting",
            ],
            help="Agent 2 will emphasize terminology and frameworks from this discipline."
        )

        audience = st.selectbox(
            "Target Audience",
            [
                "Undergraduate/ BBA (simpler vocabulary, explains business concepts)",
                "Graduate/ MBA (Standard Harvard/ IFQM case level)",
                "C-Suite Executives (Highly Strategic)",
                "General Public (Accessible to non-business readers)",
            ],
            help="Controls vocabulary complexity and number of discussion questions."
        )

        citation = st.selectbox(
            "Citation Format",
            ["APA (7th Edition)", "MLA (9th Edition)", "Chicago (17th Edition)", "IFQM Custom"],
            help="Agent 4 will compile the final references list in this format."
        )

    with col2:
        tone = st.selectbox(
            "Tone of Voice",
            [
                "Optimistic and Journalistic (Neutral, facts only)",
                "Highly Critical and Diagnostic (Focuses heavily on flaws and mistakes.)",
                "Persuasive and Visionary (Inspiring and forward looking)",
            ],
            help="Controls how Agent 2 (Storyteller) frames the narrative."
        )

        theme = st.text_input(
            "Specific Theme (Optional)",
            placeholder="e.g., Sustainability, Digital Transformation",
            help="If left blank, Agent 1 will discover themes for you to pick from."
        )

        custom_instructions = st.text_area(
            "Custom Instructions (Optional)",
            placeholder='e.g., "Focus heavily on CEO name ABC\'s leadership style."',
            height=120,
            help="Extra instructions passed directly to Agent 2 (Storyteller)."
        )

        data_privacy = st.toggle(
            "Enable Data Privacy Masking",
            value=True,
            help="ON: Replaces exact figures with directional language. OFF: Uses exact raw numbers."
        )

# ── Citation Info Box ─────────────────────────────────────────────────────────
with st.expander("Citation Format Guide"):
    st.markdown("""
| Format | Best For | In-Text Example | Reference Example |
|--------|----------|-----------------|-------------------|
| **APA (7th)** | Business, Management | (XYZ Motors Ltd., 2024) | XYZ Motors Ltd. (2024). *Annual Report 2023-24*. |
| **MLA (9th)** | Literature, Humanities | (XYZ Motors 34) | XYZ Motors Ltd. *Annual Report 2023-24*. 2024. |
| **Chicago (17th)** | History, Publishing | ¹ (footnote) | XYZ Motors Ltd., *Annual Report* (Mumbai, 2024), 34. |
| **IFQM Custom** | IFQM Teaching Cases | [Source: XYZ_AR_2024.pdf, p.34] | XYZ Motors Ltd. (2024). Annual Report, p.34. |

> **Note:** In-text citations are only used for direct quotes from a person.
    """)

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_back, col_space, col_next = st.columns([1, 3, 1])

with col_back:
    if st.button("Back", use_container_width=True):
        st.switch_page("pages/1_Upload_Documents.py")

with col_next:
    if st.button("Next: Select Angle", type="primary", use_container_width=True):

        # 1. Save all UI config to session state
        st.session_state["ui_config"] = {
            "purpose":             purpose,
            "discipline":          discipline,
            "audience":            audience,
            "citation":            citation,
            "tone":                tone,
            "theme":               theme,
            "custom_instructions": custom_instructions,
            "data_privacy":        data_privacy,
        }

        # 2. Chunk the Master Transcript in the background
        if _transcript and total_char_count(_transcript) >= 500:
            with st.spinner("Preparing your documents for analysis…"):
                from pipeline.ingest.text_chunker import chunk_master_transcript
                chunks = chunk_master_transcript(
                    _transcript,
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                )
                st.session_state["chunks"] = chunks
                time.sleep(0.8)
        else:
            st.session_state["chunks"] = []

        # 3. Navigate to Page 3
        st.switch_page("pages/3_Select_Angle.py")