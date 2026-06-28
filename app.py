import streamlit as st
import streamlit.components.v1 as components

from pipeline.persistence.session_store import (
    get_latest_fact_sheet_path,
    get_latest_case_path,
    load_fact_sheet,
    load_case_markdown,
)

st.set_page_config(
    page_title="CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Offer session restore on load
if "session_restored" not in st.session_state:
    fs_path = get_latest_fact_sheet_path()
    case_path = get_latest_case_path()
    if fs_path or case_path:
        with st.sidebar.expander("Restore last session", expanded=True):
            st.caption("Recover work after a browser refresh.")
            if fs_path and st.button("Restore FactSheet", key="restore_fs"):
                st.session_state["fact_sheet"] = load_fact_sheet(fs_path)
                st.session_state["themes"] = st.session_state["fact_sheet"].themes
                st.session_state["session_restored"] = True
                st.rerun()
            if case_path and st.button("Restore last case study", key="restore_case"):
                st.session_state["final_markdown"] = load_case_markdown(case_path)
                st.session_state["session_restored"] = True
                st.rerun()
# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

.block-container { padding-top: 2rem !important; max-width: 860px; }
section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
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
st.sidebar.caption("Use the sidebar to navigate between pages.")

# ── Page HTML (all in one components call to avoid Markdown code-block issue) ─
components.html("""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', sans-serif; background: transparent; color: #0F172A; }

.hero {
  display: flex;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
  margin-bottom: 16px;
}
.spine { width: 5px; background: #2563EB; flex-shrink: 0; }
.hero-body {
  display: grid;
  grid-template-columns: 1fr 252px;
  gap: 2rem;
  padding: 2.25rem 1.75rem;
  width: 100%;
}
.eyebrow {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2563EB;
  margin-bottom: 10px;
}
.headline {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 28px;
  font-weight: 400;
  line-height: 1.28;
  color: #0F172A;
  margin-bottom: 14px;
}
.sub {
  font-size: 14px;
  line-height: 1.65;
  color: #64748B;
}
.cta {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 1.25rem 1.125rem;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cta-label {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #94A3B8;
}
.cta-title {
  font-size: 14px;
  font-weight: 500;
  color: #0F172A;
}
.cta-desc {
  font-size: 13px;
  color: #64748B;
  line-height: 1.55;
}

.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.step {
  background: #ffffff;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 14px;
}
.step-num {
  font-size: 11px;
  font-weight: 500;
  color: #2563EB;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}
.step-title {
  font-size: 13px;
  font-weight: 500;
  color: #0F172A;
  margin-bottom: 4px;
}
.step-desc {
  font-size: 12px;
  color: #64748B;
  line-height: 1.55;
}

.formats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}
.formats-label { font-size: 12px; color: #94A3B8; }
.tag {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 99px;
  border: 1px solid #E2E8F0;
  color: #64748B;
  background: #F8FAFC;
}

.footer {
  font-size: 12px;
  color: #94A3B8;
  padding-top: 16px;
  border-top: 1px solid #E2E8F0;
  line-height: 1.6;
}
</style>
</head>
<body>

<div class="hero">
  <div class="spine"></div>
  <div class="hero-body">
    <div>
      <div class="eyebrow">CaseGen</div>
      <div class="headline">From raw company data<br>to a publishable case study.</div>
      <div class="sub">
        Upload annual reports, interview recordings, or financial spreadsheets.
        A 4-agent AI pipeline extracts the facts, builds the narrative, and exports
        a formatted document — ready to edit and publish.
      </div>
    </div>
    <div class="cta">
      <div class="cta-label">Get started</div>
      <div class="cta-title">Upload your source material</div>
      <div class="cta-desc">
        Open <strong>Upload Documents</strong> in the sidebar to add PDFs,
        audio files, Excel sheets, or paste a link to a web article.
      </div>
    </div>
  </div>
</div>

<div class="steps">
  <div class="step">
    <div class="step-num">01</div>
    <div class="step-title">Upload sources</div>
    <div class="step-desc">PDFs, audio files, Excel sheets, or a web article link</div>
  </div>
  <div class="step">
    <div class="step-num">02</div>
    <div class="step-title">Set scope</div>
    <div class="step-desc">Choose tone, audience, discipline, and citation format</div>
  </div>
  <div class="step">
    <div class="step-num">03</div>
    <div class="step-title">Generate</div>
    <div class="step-desc">Agents extract facts, select a theme, and write the narrative</div>
  </div>
  <div class="step">
    <div class="step-num">04</div>
    <div class="step-title">Export</div>
    <div class="step-desc">Review, edit, and download as a Word document or PDF</div>
  </div>
</div>

<div class="formats">
  <span class="formats-label">Accepts</span>
  <span class="tag">PDF</span>
  <span class="tag">Audio</span>
  <span class="tag">Excel / CSV</span>
  <span class="tag">Web links</span>
</div>

<div class="footer">
  Everything runs locally on your device — no cloud costs, no hidden fees.<br>
  Built with a 4-agent pipeline: fact extraction, narrative writing, exhibit generation, and fact-checking.
</div>

</body>
</html>
""", height=520, scrolling=False)