import streamlit as st
import streamlit.components.v1 as components

from pipeline.persistence.session_store import (
    get_latest_fact_sheet_path,
    get_latest_case_path,
    load_fact_sheet,
    load_case_markdown,
)
from pipeline.persistence.auth import (
    init_users_table,
    verify_login,
    register_user,
)

st.set_page_config(
    page_title="CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Auth Initialization & Gateway ─────────────────────────────────────────────
init_users_table()

if not st.session_state.get("authenticated", False):
    # Hide sidebar page navigation when not logged in
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 3rem !important; max-width: 920px; }
    [data-testid="stSidebarNav"] { display: none !important; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div style="padding:0.25rem 0 0.75rem;">
        <div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
        <div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
    </div>
    <div style="font-size:12px;color:#64748B;line-height:1.5;margin-top:1rem;padding-top:1rem;border-top:1px solid #E2E8F0;">
        Please sign in with your credentials to access the generation workspace.
    </div>
    """, unsafe_allow_html=True)

    login_col1, login_col2 = st.columns([1.2, 1], gap="large")

    with login_col1:
        st.markdown("""
        <div style="padding-top:1.5rem;">
            <div style="font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#2563EB; margin-bottom:12px;">
                CASEGEN ACCESS
            </div>
            <div style="font-family:'DM Serif Display', Georgia, serif; font-size:32px; font-weight:400; line-height:1.2; color:#0F172A; margin-bottom:16px;">
                From raw company data to a publishable case study.
            </div>
            <div style="font-size:15px; line-height:1.6; color:#64748B; margin-bottom:24px;">
                An intelligent multi-agent pipeline that extracts facts, discovers strategic themes,
                crafts rigorous business narratives, and exports publication-ready Word and PDF case studies.
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:1rem 1.25rem;">
                <div style="font-size:12px; font-weight:600; color:#0F172A; margin-bottom:4px;">Academic Evaluation Portal</div>
                <div style="font-size:12px; color:#64748B; line-height:1.5;">
                    Course Project: CSE3005 Software Engineering<br>
                    Team: Ananshi Sharma, Aditya Nadar, Sumit Singh, Dhruv Sharma
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with login_col2:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        tab_signin, tab_signup = st.tabs(["Sign In", "Register"])

        with tab_signin:
            with st.form("login_form"):
                username_input = st.text_input("Username", placeholder="e.g. ananshi")
                password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                login_submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if login_submitted:
                # TC03: Empty fields check
                if not username_input.strip() or not password_input.strip():
                    st.warning("Please enter both username and password.")
                # TC01, TC02, TC04: Credential verification
                elif verify_login(username_input.strip(), password_input):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username_input.strip()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with tab_signup:
            with st.form("register_form"):
                reg_fullname = st.text_input("Full Name", placeholder="e.g. Ananshi Sharma")
                reg_studentid = st.text_input("Student ID", placeholder="e.g. 240377")
                reg_username = st.text_input("Username", placeholder="Choose username")
                reg_password = st.text_input("Password", type="password", placeholder="Minimum 6 characters")
                reg_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if reg_submitted:
                if not all([reg_fullname.strip(), reg_studentid.strip(), reg_username.strip(), reg_password.strip()]):
                    st.warning("All fields are required.")
                else:
                    reg_result = register_user(
                        reg_username.strip(),
                        reg_password,
                        reg_fullname.strip(),
                        reg_studentid.strip(),
                    )
                    if reg_result is True:
                        st.success(f"Account created for **{reg_username.strip()}**. Switch to Sign In to continue.")
                    else:
                        st.error(reg_result)

    # Stop rendering the rest of the application until authenticated
    st.stop()

# ── Authenticated User Sidebar Status ─────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:0.6rem 0.8rem; margin-bottom:0.75rem;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:#64748B;">Signed in as</div>
        <div style="font-size:13px; font-weight:600; color:#0F172A;">{st.session_state.get('username', 'User')}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Sign out", key="sign_out_btn", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()
    st.divider()

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
<div>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* Reset and base */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem !important; max-width: 960px; }
section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
/* Hero container styling using :has() to target specific st.container */
div[data-testid="stVerticalBlock"]:has(> div.element-container .hero-marker) {
    border: 1px solid #E2E8F0;
    border-left: 6px solid #2563EB;
    border-radius: 12px;
    background: #ffffff;
    padding: 2.5rem 2rem !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    margin-bottom: 1.5rem;
}
/* CTA box styling — shrink-wrapped to its content, light shaded fill */
div[data-testid="stVerticalBlock"]:has(> div.element-container .cta-marker) {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background: #F8FAFC;
    box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.03);
    padding: 1rem 2rem !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: auto;
    max-width: 340px;
    margin: 0 auto;
}
/* Override CTA button styling */
div[data-testid="stVerticalBlock"]:has(> div.element-container .cta-marker) button {
    background-color: #2563EB !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 0.5rem 1rem !important;
    margin-top: 4px;
}
div[data-testid="stVerticalBlock"]:has(> div.element-container .cta-marker) button:hover {
    background-color: #1D4ED8 !important;
    color: #ffffff !important;
}
</style>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="padding:0.25rem 0 0.75rem;">
<div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
<div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
</div>
""", unsafe_allow_html=True)

# ── Hero Section ──────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="hero-marker"></div>', unsafe_allow_html=True)
    hero_col, cta_col = st.columns([1.6, 1], gap="large")

    with hero_col:
        st.markdown("""
        <div style="display:flex; flex-direction:column; gap:0.5rem;">
            <div style="font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#2563EB;">
                CASEGEN
            </div>
            <div style="font-family:'DM Serif Display', Georgia, serif; font-size:32px; font-weight:400; line-height:1.2; color:#0F172A;">
                From raw company data to a publishable case study.
            </div>
            <div style="font-size:15px; line-height:1.6; color:#64748B; margin-top:8px;">
                Upload your source material and let AI draft your case study.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cta_col:
        with st.container():
            st.markdown('<div class="cta-marker"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align:center;">
                <div style="font-size:16px; font-weight:600; color:#0F172A; margin-bottom:6px;">
                    Generate a case study in minutes.
                </div>
                <div style="font-size:15px; color:#64748B; margin-bottom:10px;">
                    Upload now!
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Get started", type="primary", use_container_width=True, key="get_started"):
                st.switch_page("pages/1_Upload_Documents.py")

# ── Steps + formats + footer ───────────────────────────────────────────────────
components.html("""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', sans-serif; background: transparent; color: #0F172A; }

.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.step {
  background: #ffffff;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.step-num {
  font-size: 12px;
  font-weight: 600;
  color: #2563EB;
  margin-bottom: 10px;
}
.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #0F172A;
  margin-bottom: 6px;
}
.step-desc {
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
}

.formats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 32px;
}
.formats-label { font-size: 13px; color: #94A3B8; font-weight: 500; margin-right: 4px; }
.tag {
  font-size: 12px;
  font-weight: 500;
  padding: 4px 14px;
  border-radius: 99px;
  border: 1px solid #E2E8F0;
  color: #334155;
  background: #ffffff;
}

.footer {
  font-size: 13px;
  color: #94A3B8;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #E2E8F0;
  line-height: 1.6;
}
</style>
</head>
<body>

<div class="steps">
  <div class="step">
    <div class="step-num">01</div>
    <div class="step-title">Upload sources</div>
    <div class="step-desc">PDFs, audio, Excel, or a web link</div>
  </div>
  <div class="step">
    <div class="step-num">02</div>
    <div class="step-title">Set scope</div>
    <div class="step-desc">Tone, audience, discipline, citations</div>
  </div>
  <div class="step">
    <div class="step-num">03</div>
    <div class="step-title">Generate</div>
    <div class="step-desc">Facts extracted, theme picked, narrative written</div>
  </div>
  <div class="step">
    <div class="step-num">04</div>
    <div class="step-title">Export</div>
    <div class="step-desc">Review, edit, download Word or PDF</div>
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
  A 4-Agent Pipeline handles extraction, narrative, exhibit and fact checking in sequence.
</div>

</body>
</html>
""", height=280, scrolling=False)