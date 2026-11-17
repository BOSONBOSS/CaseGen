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
    get_user_info,
    render_sidebar_auth,
)

st.set_page_config(
    page_title="CaseGen",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize local SQLite users table (idempotent, seeds team demo accounts)
init_users_table()

_is_authenticated = st.session_state.get("authenticated", False)

# Hide sidebar page navigation links until the user is signed in
if not _is_authenticated:
    st.markdown(
        "<style>[data-testid='stSidebarNav'] { display: none !important; }</style>",
        unsafe_allow_html=True,
    )

# ── Auth Screen (shown ONLY after clicking "Get started" while signed out) ────
if st.session_state.get("show_auth", False) and not _is_authenticated:
    st.markdown("""
    <div>
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2.5rem !important; max-width: 960px; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #E2E8F0; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container .auth-card-marker) {
        border: 1px solid #E2E8F0;
        border-left: 6px solid #2563EB;
        border-radius: 12px;
        background: #ffffff;
        padding: 2.25rem 2rem !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    }
    div[data-testid="stFormSubmitButton"] button {
        background-color: #2563EB !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #1D4ED8 !important;
        color: #ffffff !important;
    }
    </style>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div style="padding:0.25rem 0 0.75rem;">
    <div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
    <div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.divider()
    if st.sidebar.button("← Back to Home", key="auth_back_home", use_container_width=True):
        st.session_state["show_auth"] = False
        st.rerun()

    with st.container():
        st.markdown('<div class="auth-card-marker"></div>', unsafe_allow_html=True)
        info_col, form_col = st.columns([1.15, 1], gap="large")

        with info_col:
            st.markdown("""
            <div style="display:flex; flex-direction:column; gap:0.65rem; padding-top:0.5rem;">
                <div style="font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#2563EB;">
                    CASEGEN WORKSPACE
                </div>
                <div style="font-family:'DM Serif Display', Georgia, serif; font-size:30px; font-weight:400; line-height:1.2; color:#0F172A;">
                    Sign in to start generating.
                </div>
                <div style="font-size:14px; line-height:1.65; color:#64748B; margin-top:4px;">
                    Create an account or sign in with your credentials to upload source documents,
                    configure your case study, and access saved work.
                </div>
                <div style="margin-top:1rem; padding:0.9rem 1.1rem; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px;">
                    <div style="font-size:12px; font-weight:600; color:#0F172A; margin-bottom:4px;">New here?</div>
                    <div style="font-size:12px; color:#64748B; line-height:1.5;">
                        Switch to the <b>Register</b> tab to create your account first, then sign in to begin uploading documents.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with form_col:
            tab_signin, tab_register = st.tabs(["Sign In", "Register"])

            with tab_signin:
                with st.form("login_form"):
                    username_input = st.text_input("Username", placeholder="Enter your username")
                    password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                    login_submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if login_submitted:
                    if not username_input.strip() or not password_input.strip():
                        st.warning("Please enter both username and password.")
                    elif verify_login(username_input.strip(), password_input):
                        uname = username_input.strip()
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = uname
                        st.session_state["user_info"] = get_user_info(uname)
                        st.session_state["show_auth"] = False
                        st.switch_page("pages/1_Upload_Documents.py")
                    else:
                        st.error("Invalid username or password.")

            with tab_register:
                with st.form("register_form"):
                    reg_fullname = st.text_input("Full Name", placeholder="e.g. Ananshi Sharma")
                    reg_email = st.text_input("Email ID", placeholder="e.g. ananshi@example.com")
                    reg_username = st.text_input("Username", placeholder="Choose a username")
                    reg_password = st.text_input("Password", type="password", placeholder="At least 6 characters")
                    reg_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                if reg_submitted:
                    if not all([
                        reg_fullname.strip(),
                        reg_email.strip(),
                        reg_username.strip(),
                        reg_password.strip(),
                    ]):
                        st.warning("All fields are required.")
                    else:
                        reg_result = register_user(
                            reg_username.strip(),
                            reg_password,
                            reg_fullname.strip(),
                            reg_email.strip(),
                        )
                        if reg_result is True:
                            st.success(
                                f"Account created for **{reg_username.strip()}**. "
                                "Switch to the **Sign In** tab to continue."
                            )
                        else:
                            st.error(reg_result)

    st.stop()

# Offer session restore on load (only for authenticated users)
if _is_authenticated and "session_restored" not in st.session_state:
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
if _is_authenticated:
    render_sidebar_auth(on_home=True)

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
                if _is_authenticated:
                    st.switch_page("pages/1_Upload_Documents.py")
                else:
                    st.session_state["show_auth"] = True
                    st.rerun()

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