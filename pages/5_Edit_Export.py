import streamlit as st
from pipeline.agents.agent_editor import run_agent_4
from pipeline.agents.agent_storyteller import regenerate_section
from pipeline.persistence.session_store import save_case_markdown
from pipeline.persistence.case_history import save_case
from pipeline.export.markdown_to_docx import markdown_to_docx
from pipeline.export.markdown_to_pdf import markdown_to_pdf

st.set_page_config(
    page_title="Edit & Export | CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2.5rem !important; max-width: 960px; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
    .page-title { font-family: 'DM Serif Display', Georgia, serif; font-size: 26px; color: #0F172A; }
    .section-label { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; color: #2563EB; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("**Step 5 of 5** — Edit & Export")
st.markdown('<div class="page-title">Review, Edit & Export</div>', unsafe_allow_html=True)

if not st.session_state.get("final_markdown"):
    required = ["narrative", "fact_sheet", "filtered_fact_sheet", "ui_config"]
    missing = [k for k in required if k not in st.session_state]
    if missing:
        st.error(f"Missing: {', '.join(missing)}. Complete generation first.")
        if st.button("Go to Generate"):
            st.switch_page("pages/4_Generate_Case_Study.py")
        st.stop()

can_regenerate = all(k in st.session_state for k in ["narrative", "filtered_fact_sheet", "ui_config"])

SECTIONS = [
    ("background", "Company Background"),
    ("industry_context", "Industry Context"),
    ("challenge", "The Challenge"),
    ("intervention", "Intervention"),
    ("results", "Results"),
    ("learnings", "Learnings"),
]

if "final_markdown" not in st.session_state or not st.session_state.get("final_markdown"):
    if not can_regenerate:
        st.error("Cannot run Agent 4: session state incomplete. Load a document from Page 1 first.")
        st.stop()
    with st.spinner("Agent 4 is fact-checking and formatting the final document…"):
        try:
            final_md = run_agent_4(
                narrative=st.session_state["narrative"],
                exhibits=st.session_state.get("exhibits", ""),
                discussion_questions=st.session_state.get("discussion_questions", []),
                fact_sheet=st.session_state["fact_sheet"],
                filtered_fact_sheet=st.session_state["filtered_fact_sheet"],
                ui_config=st.session_state["ui_config"],
                master_transcript=st.session_state.get("master_transcript", {}),
            )
            st.session_state["final_markdown"] = final_md
            company = st.session_state["filtered_fact_sheet"].company_name
            theme = st.session_state["ui_config"].get("selected_theme", "")
            path = save_case_markdown(final_md, company)
            save_case(company, theme, path)
        except Exception as e:
            st.error(f"Agent 4 failed: {type(e).__name__}: {e}")
            st.exception(e)
            st.stop()

if can_regenerate:
    st.markdown('<div class="section-label">Regenerate Sections</div>', unsafe_allow_html=True)
    reg_cols = st.columns(3)
    for i, (sid, label) in enumerate(SECTIONS):
        with reg_cols[i % 3]:
            if st.button(f"↻ {label}", key=f"regen_{sid}"):
                with st.spinner(f"Regenerating {label}..."):
                    updated = regenerate_section(
                        sid,
                        st.session_state["filtered_fact_sheet"],
                        st.session_state["ui_config"],
                        st.session_state["narrative"],
                    )
                    st.session_state["narrative"] = updated
                    st.session_state.pop("final_markdown", None)
                st.rerun()

edited = st.text_area(
    "Final case study (editable)",
    value=st.session_state["final_markdown"],
    height=500,
    label_visibility="collapsed",
)
st.session_state["final_markdown"] = edited

st.markdown("<br>", unsafe_allow_html=True)
dl1, dl2, _ = st.columns([1, 1, 2])

company_safe = st.session_state["filtered_fact_sheet"].company_name.replace(" ", "_")[:30]

with dl1:
    try:
        docx_bytes = markdown_to_docx(edited)
        st.download_button(
            "Download Word (.docx)",
            data=docx_bytes,
            file_name=f"{company_safe}_case_study.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Word export error: {e}")

with dl2:
    try:
        pdf_bytes = markdown_to_pdf(edited)
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{company_safe}_case_study.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"PDF export unavailable: {e}")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Back to Generate", use_container_width=False):
    st.switch_page("pages/4_Generate_Case_Study.py")
