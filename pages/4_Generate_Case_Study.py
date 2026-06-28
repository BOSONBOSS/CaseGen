import streamlit as st
from pipeline.agents.run_generation import run_generation

st.set_page_config(
    page_title="Generate Case Study | CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2.5rem !important; max-width: 900px; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
    .page-title { font-family: 'DM Serif Display', Georgia, serif; font-size: 26px; color: #0F172A; margin-bottom: 0.4rem; }
    .page-desc { font-size: 14px; color: #64748B; margin-bottom: 2rem; }
    .section-label { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; color: #2563EB; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("**Step 4 of 5** — Generate")
st.markdown('<div class="page-title">Generate Case Study</div>', unsafe_allow_html=True)
st.markdown('<div class="page-desc">Agents 2 and 3 write the narrative and exhibits in parallel.</div>', unsafe_allow_html=True)

required = ["filtered_fact_sheet", "ui_config", "chunks"]
missing = [k for k in required if k not in st.session_state or not st.session_state[k]]
if missing:
    st.error(f"Missing session data: {', '.join(missing)}. Complete earlier steps first.")
    if st.button("Back to Page 3"):
        st.switch_page("pages/3_Select_Angle.py")
    st.stop()

if "narrative" not in st.session_state or not st.session_state.get("narrative"):
    col2, col3 = st.columns(2)
    bar2 = col2.progress(0, text="Agent 2: waiting...")
    bar3 = col3.progress(0, text="Agent 3: waiting...")
    status = st.empty()

    def on_a2():
        bar2.progress(100, text="Agent 2: narrative complete ✓")

    def on_a3():
        bar3.progress(100, text="Agent 3: exhibits complete ✓")

    try:
        status.markdown("**Agent 2** is writing the narrative… &nbsp; **Agent 3** is building exhibits…")
        bar2.progress(30, text="Agent 2: writing narrative...")
        bar3.progress(30, text="Agent 3: building exhibits...")

        result = run_generation(
            st.session_state["filtered_fact_sheet"],
            st.session_state["ui_config"],
            on_agent2_progress=on_a2,
            on_agent3_progress=on_a3,
        )

        st.session_state["narrative"] = result["narrative"]
        st.session_state["exhibits"] = result["exhibits"]
        st.session_state["discussion_questions"] = result["discussion_questions"]
        status.empty()
        bar2.empty()
        bar3.empty()
        st.rerun()
    except Exception as e:
        st.error(f"Generation failed: {e}")
        st.stop()

narrative = st.session_state["narrative"]
exhibits = st.session_state.get("exhibits", "")
questions = st.session_state.get("discussion_questions", [])

st.success("Generation complete.")

st.markdown('<div class="section-label">Narrative Preview</div>', unsafe_allow_html=True)
for section_id, title in [
    ("background", "Background"),
    ("challenge", "Challenge"),
    ("intervention", "Intervention"),
    ("results", "Results"),
]:
    text = narrative.get(section_id, "")
    if text:
        with st.expander(title, expanded=(section_id == "background")):
            st.markdown(text)

if exhibits:
    with st.expander("Exhibits", expanded=False):
        st.markdown(exhibits)

if questions:
    with st.expander("Discussion Questions", expanded=False):
        for i, q in enumerate(questions, 1):
            st.markdown(f"{i}. {q}")

st.markdown("<br>", unsafe_allow_html=True)
col_back, _, col_next = st.columns([1, 3, 1])
with col_back:
    if st.button("Back", use_container_width=True):
        st.switch_page("pages/3_Select_Angle.py")
with col_next:
    if st.button("Next: Edit & Export", type="primary", use_container_width=True):
        st.session_state.pop("final_markdown", None)
        st.switch_page("pages/5_Edit_Export.py")
