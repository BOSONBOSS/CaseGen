import os
import streamlit as st
from pipeline.ingest.docling_parser import parse_pdf
from pipeline.ingest.spreadsheet_parser import parse_spreadsheet
from pipeline.ingest.whisper_audio import parse_audio
from pipeline.ingest.web_parser import parse_url
from pipeline.ingest.merge_sources import (
    save_backup,
    total_char_count,
    detect_homepage_junk,
)
from config import WHISPER_MODEL

st.set_page_config(
    page_title="Upload Documents | CaseGen",
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
    .status-ok { color: #16a34a; font-size: 13px; }
    .status-err { color: #dc2626; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="padding:0.25rem 0 0.75rem;">
    <div style="font-size:15px;font-weight:500;color:#0F172A;margin-bottom:4px;">CaseGen</div>
    <div style="font-size:12px;color:#94A3B8;">AI Case Study Generator</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("**Step 1 of 5** — Upload Documents")
st.sidebar.caption("Upload all source files before moving to configuration.")

with st.sidebar.expander("Processing Options", expanded=False):
    whisper_model = st.selectbox(
        "Whisper model size",
        ["tiny", "base", "small", "medium", "large"],
        index=["tiny", "base", "small", "medium", "large"].index(WHISPER_MODEL)
        if WHISPER_MODEL in ["tiny", "base", "small", "medium", "large"] else 1,
        help="medium recommended for Indian English; large is slowest",
    )
    max_pages = st.number_input(
        "PDF max pages (0 = all pages)",
        min_value=0,
        value=0,
        help="Dev toggle: cap PDF pages for faster testing",
    )

st.markdown('<div class="page-title">Upload Source Documents</div>', unsafe_allow_html=True)
st.markdown('<div class="page-desc">Add every file you want the AI to read. Supported formats: PDF, Excel, CSV, audio files, and web articles.</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container(border=True):
        st.markdown('<div class="section-label">Documents &amp; Data</div>', unsafe_allow_html=True)
        docs = st.file_uploader(
            "docs",
            type=["pdf", "xlsx", "csv", "xls"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

with col2:
    with st.container(border=True):
        st.markdown('<div class="section-label">Audio Interviews</div>', unsafe_allow_html=True)
        audio = st.file_uploader(
            "audio",
            type=["mp3", "wav", "m4a", "mp4", "mpeg", "mpga", "webm"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

st.markdown("<br>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="section-label">Web Article or PDF URL</div>', unsafe_allow_html=True)
    url = st.text_input("url", placeholder="https://", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

if "extract_status" not in st.session_state:
    st.session_state["extract_status"] = {}
if "extract_warnings" not in st.session_state:
    st.session_state["extract_warnings"] = []

if st.button("Extract and merge all sources", type="primary", use_container_width=True):
    if not docs and not audio and not url:
        st.warning("Add at least one file or URL before extracting.")
    else:
        os.makedirs("session_backup", exist_ok=True)
        master_transcript: dict = {}
        status: dict = {}
        warnings: list = []

        with st.spinner("Processing files... (Audio transcription may take a few minutes)"):
            if docs:
                for file in docs:
                    try:
                        st.toast(f"Parsing {file.name}...")
                        if file.name.lower().endswith(".pdf"):
                            pages = int(max_pages) if max_pages and max_pages > 0 else None
                            text = parse_pdf(file, max_pages=pages)
                        else:
                            text = parse_spreadsheet(file)
                        master_transcript[file.name] = text
                        status[file.name] = {"ok": True, "chars": len(text)}
                    except Exception as e:
                        status[file.name] = {"ok": False, "error": str(e)}

            if audio:
                for file in audio:
                    try:
                        st.toast(f"Transcribing {file.name}...")
                        text = parse_audio(file, model_size=whisper_model)
                        master_transcript[file.name] = text
                        status[file.name] = {"ok": True, "chars": len(text)}
                    except Exception as e:
                        status[file.name] = {"ok": False, "error": str(e)}

            if url and url.strip():
                try:
                    st.toast("Extracting web content...")
                    text, web_warning = parse_url(url.strip())
                    key = url.strip()[:80]
                    master_transcript[key] = text
                    status[key] = {"ok": True, "chars": len(text)}
                    if web_warning:
                        warnings.append(web_warning)
                except Exception as e:
                    status[url.strip()[:80]] = {"ok": False, "error": str(e)}

            combined = " ".join(master_transcript.values())
            junk_warning = detect_homepage_junk(combined)
            if junk_warning:
                warnings.append(junk_warning)

            st.session_state["master_transcript"] = master_transcript
            st.session_state["extract_status"] = status
            st.session_state["extract_warnings"] = warnings
            save_backup(master_transcript, warnings)

            if master_transcript:
                st.success(f"Processed {len(master_transcript)} source(s) successfully.")
            else:
                st.error("No sources could be extracted. Fix errors below and retry.")

if st.session_state.get("extract_status"):
    st.markdown('<div class="section-label">Extraction Status</div>', unsafe_allow_html=True)
    for name, info in st.session_state["extract_status"].items():
        if info.get("ok"):
            st.markdown(f'<span class="status-ok">✓ {name}</span> — {info["chars"]:,} characters', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="status-err">✗ {name}</span> — {info.get("error", "Unknown error")}', unsafe_allow_html=True)

for w in st.session_state.get("extract_warnings", []):
    st.warning(w)

if st.session_state.get("master_transcript"):
    total = total_char_count(st.session_state["master_transcript"])
    st.caption(f"Total extracted: {total:,} characters across {len(st.session_state['master_transcript'])} source(s)")
    with st.expander("Preview master transcript"):
        from pipeline.ingest.merge_sources import merge_to_text
        preview = merge_to_text(st.session_state["master_transcript"])
        st.text(preview[:2000] + ("\n\n... (truncated)" if len(preview) > 2000 else ""))

st.markdown("<br>", unsafe_allow_html=True)
col_back, col_space, col_next = st.columns([1, 3, 1])

transcript = st.session_state.get("master_transcript")
total_chars = total_char_count(transcript) if transcript else 0
can_proceed = transcript and total_chars >= 500 and all(
    s.get("ok", False) for s in st.session_state.get("extract_status", {}).values()
) if st.session_state.get("extract_status") else bool(transcript and total_chars >= 500)

with col_next:
    if st.button("Next: Configure", type="primary" if can_proceed else "secondary", use_container_width=True):
        if not transcript:
            st.error("Run extraction first.")
        elif total_chars < 500:
            st.error(f"Transcript too short ({total_chars} chars). Upload a fuller document (minimum 500 characters).")
        elif st.session_state.get("extract_status") and not all(s.get("ok") for s in st.session_state["extract_status"].values()):
            st.error("Fix failed extractions before continuing.")
        else:
            st.switch_page("pages/2_Configure_Case_Study.py")
