import streamlit as st
from pipeline.agents.agent_extractor import run_agent_1
from pipeline.agents.theme_filter import filter_by_theme
from pipeline.persistence.session_store import save_fact_sheet

st.set_page_config(
    page_title="Select Angle | CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    .block-container { padding-top: 2.5rem !important; max-width: 900px; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
    .page-title { font-family: 'DM Serif Display', Georgia, serif; font-size: 26px; font-weight: 400; color: #0F172A; margin-bottom: 0.4rem; }
    .page-desc { font-size: 14px; color: #64748B; margin-bottom: 2rem; line-height: 1.6; }
    .section-label { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; color: #2563EB; margin-bottom: 1rem; }
    .fact-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; font-size: 13px; color: #0F172A; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="padding:0.25rem 0 0.75rem;">
    <div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
    <div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("**Step 3 of 5** — Select Angle")

with st.sidebar.expander("Dev Tools", expanded=False):
    if st.button("Re-run Agent 1", key="sidebar_rerun"):
        for key in ["fact_sheet", "themes", "selected_theme", "filtered_fact_sheet"]:
            st.session_state.pop(key, None)
        st.rerun()
    if st.button("Show chunk count", key="sidebar_chunks"):
        st.info(f"{len(st.session_state.get('chunks', []))} chunks in session")

st.markdown('<div class="page-title">Select Your Case Study Angle</div>', unsafe_allow_html=True)
st.markdown('<div class="page-desc">Agent 1 extracts facts and discovers themes. Pick the focus for your case study.</div>', unsafe_allow_html=True)

if "chunks" not in st.session_state or not st.session_state["chunks"]:
    st.error("No document chunks found. Please go back to Page 1 and upload your documents.")
    if st.button("Go to Page 1"):
        st.switch_page("pages/1_Upload_Documents.py")
    st.stop()

chunks = st.session_state["chunks"]
st.caption(f"{len(chunks)} text chunks loaded from your documents.")

if "fact_sheet" not in st.session_state:
    progress_text = st.empty()
    progress_bar = st.progress(0, text="Initialising Agent 1...")
    total_batches_ref = {"n": max(1, (len(chunks) + 9) // 10)}

    def on_progress(batch_num, total_batches):
        total_batches_ref["n"] = total_batches
        pct = min(95, int(10 + (batch_num / total_batches) * 85))
        progress_bar.progress(pct, text=f"Agent 1: batch {batch_num}/{total_batches}...")

    try:
        progress_text.markdown("**Agent 1** is reading your documents. This takes 1-3 minutes for large annual reports...")
        fact_sheet = run_agent_1(chunks, on_progress=on_progress)
        progress_bar.progress(100, text="Done!")
        progress_text.empty()
        progress_bar.empty()

        st.session_state["fact_sheet"] = fact_sheet
        st.session_state["themes"] = fact_sheet.themes

        import json, os
        os.makedirs("session_backup", exist_ok=True)
        with open("session_backup/fact_sheet.json", "w", encoding="utf-8") as f:
            f.write(fact_sheet.model_dump_json(indent=2))
        save_fact_sheet(fact_sheet)

    except Exception as e:
        progress_bar.empty()
        progress_text.empty()
        st.error(f"Agent 1 failed: {str(e)}")
        st.stop()

fact_sheet = st.session_state["fact_sheet"]
themes = st.session_state.get("themes", [])

st.success("Analysis complete. Agent 1 has finished reading your documents.")

with st.expander("View Extracted FactSheet", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="fact-box">'
            f'<strong>Company:</strong> {fact_sheet.company_name}<br>'
            f'<strong>Founded:</strong> {fact_sheet.founding_year or "N/A"}<br>'
            f'<strong>Industry:</strong> {fact_sheet.industry or "N/A"}<br>'
            f'<strong>HQ:</strong> {fact_sheet.headquarters or "N/A"}<br>'
            f'<strong>Revenue:</strong> {fact_sheet.revenue or "N/A"}'
            f'</div>',
            unsafe_allow_html=True
        )
        if fact_sheet.challenges:
            st.markdown('<div class="section-label">Key Challenges</div>', unsafe_allow_html=True)
            for c in fact_sheet.challenges[:4]:
                st.markdown(f'<div class="fact-box">{c}</div>', unsafe_allow_html=True)
    with col2:
        if fact_sheet.key_people:
            st.markdown(
                f'<div class="fact-box"><strong>Key People:</strong><br>'
                + "<br>".join(fact_sheet.key_people[:8]) + "</div>",
                unsafe_allow_html=True
            )
        if fact_sheet.outcomes:
            for o in fact_sheet.outcomes[:4]:
                st.markdown(f'<div class="fact-box">{o}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="section-label">Discovered Themes — Select One</div>', unsafe_allow_html=True)

if not themes:
    themes = ["General Business Analysis"]
    st.session_state["themes"] = themes

themes = themes[:6]
selected_theme = st.session_state.get("selected_theme", themes[0])

for row in [themes[i:i+3] for i in range(0, len(themes), 3)]:
    cols = st.columns(len(row))
    for col, theme in zip(cols, row):
        with col:
            if st.button(theme, key=f"theme_{theme}", type="primary" if selected_theme == theme else "secondary", use_container_width=True):
                selected_theme = theme
                st.session_state["selected_theme"] = theme
                st.rerun()

st.session_state["selected_theme"] = selected_theme
st.info(f"Selected angle: **{selected_theme}**")

st.markdown("<br>", unsafe_allow_html=True)
col_back, col_space, col_next = st.columns([1, 3, 1])

with col_back:
    if st.button("Back", use_container_width=True):
        st.switch_page("pages/2_Configure_Case_Study.py")

with col_next:
    if st.button("Generate Case Study", type="primary", use_container_width=True):
        with st.spinner(f"Filtering facts for theme: {selected_theme}..."):
            filtered = filter_by_theme(fact_sheet, selected_theme)
            st.session_state["filtered_fact_sheet"] = filtered
            if "ui_config" not in st.session_state:
                st.session_state["ui_config"] = {}
            st.session_state["ui_config"]["selected_theme"] = selected_theme
            for key in ["narrative", "exhibits", "discussion_questions", "final_markdown"]:
                st.session_state.pop(key, None)
        st.switch_page("pages/4_Generate_Case_Study.py")
