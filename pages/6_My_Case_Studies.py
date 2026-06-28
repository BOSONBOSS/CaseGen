import streamlit as st
from pipeline.persistence.case_history import list_cases, get_case
from pipeline.persistence.session_store import load_case_markdown

st.set_page_config(page_title="My Case Studies | CaseGen", layout="wide")

st.title("My Case Studies")
st.caption("Previously generated case studies saved locally.")

cases = list_cases()

if not cases:
    st.info("No saved case studies yet. Generate one from the wizard.")
else:
    for case in cases:
        with st.expander(f"{case['company_name']} — {case['theme'] or 'General'} ({case['created_at'][:10]})"):
            st.caption(f"Saved: {case['markdown_path']}")
            if st.button("Load into editor", key=f"load_{case['id']}"):
                if case["markdown_path"]:
                    try:
                        md = load_case_markdown(case["markdown_path"])
                        st.session_state["final_markdown"] = md
                        st.switch_page("pages/5_Edit_Export.py")
                    except FileNotFoundError:
                        st.error(f"File not found on disk: {case['markdown_path']}")
                    except Exception as e:
                        st.error(f"Could not load case: {type(e).__name__}: {e}")
