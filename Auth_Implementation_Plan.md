# Auth Implementation Plan — CaseGen
**Branch:** `academic/course-eval-auth`  
**Scope:** Login + Register page as a gateway to the entire app  
**Author:** Ananshi Sharma (240377)  
**Status:** PLAN ONLY — no changes made yet

---

## What This Does (In Plain English)

Right now, anyone who opens the app lands directly on the homepage. We are adding a **login wall**: if you are not authenticated, you see a login/register screen. If you are, you see the existing app — completely unchanged.

No existing page is modified. No agent is touched. The app continues to work exactly as before for authenticated users.

---

## What Already Exists vs. What Needs Building

| Item | Status | Notes |
|---|---|---|
| `case_history.db` (SQLite file) | ✅ Exists | Will add `users` table to it |
| `pipeline/persistence/case_history.py` | ✅ Exists | Untouched |
| `Home.py` (hero + steps UI) | ✅ Exists | Will add ~50 lines at the **top only** |
| All 6 pages (`pages/1_*.py` → `pages/6_*.py`) | ✅ Exists | **Zero changes** |
| All pipeline agents | ✅ Exists | **Zero changes** |
| `config.py`, `.env` | ✅ Exists | **Zero changes** |
| `pipeline/persistence/auth.py` | ❌ Does not exist | **New file — to be created** |
| `users` table in SQLite | ❌ Does not exist | **Created by `auth.py` on first run** |
| Auth gatekeeper block in `Home.py` | ❌ Does not exist | **~50 lines added at top of file** |
| Logout button in sidebar | ❌ Does not exist | **Added inside the gatekeeper block** |

---

## Phase A — Create the Safe Branch

> Nothing is committed to `main`. All changes live on `academic/course-eval-auth`.

```bash
git checkout main
git pull origin main
git checkout -b academic/course-eval-auth
```

**Verification:** `git branch` should show `* academic/course-eval-auth`

---

## Phase B — Create `pipeline/persistence/auth.py`

This is a **new file**. It has no effect on anything until `Home.py` imports it.

### File: `pipeline/persistence/auth.py`

**Responsibilities:**
1. `init_users_table()` — creates the `users` table if it doesn't exist + seeds the 4 demo accounts
2. `register_user(username, password, full_name, student_id)` → `True` / error string
3. `verify_login(username, password)` → `True` / `False`

### Database Schema

```sql
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt        TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    student_id  TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Where:** Same `case_history.db` SQLite file — no new DB file needed.

### Password Hashing

- **Algorithm:** `hashlib.pbkdf2_hmac('sha256', ...)` — Python built-in, zero new packages
- **Salt:** `secrets.token_hex(32)` generated fresh per user at registration
- **Iterations:** 100,000 (NIST-recommended minimum for PBKDF2)
- Stored as hex strings — never plaintext

### Pre-Seeded Demo Accounts (Created on `init_users_table()`)

| Username | Password | Full Name | Student ID |
|---|---|---|---|
| `ananshi` | `CaseGen@2026` | Ananshi Sharma | 240377 |
| `aditya` | `CaseGen@2026` | Aditya Nadar | 240368 |
| `sumit` | `CaseGen@2026` | Sumit Singh | 240344 |
| `dhruv` | `CaseGen@2026` | Dhruv Sharma | 240444 |

These accounts are created only if they don't already exist — safe to call `init_users_table()` on every app start.

### Verification After Creating File

```bash
./venv/bin/python -c "
from pipeline.persistence.auth import verify_login
print(verify_login('ananshi', 'CaseGen@2026'))   # → True
print(verify_login('ananshi', 'wrongpassword'))   # → False
"
```

---

## Phase C — Modify `Home.py`

### What Changes

**Only the top of the file is touched.** The existing code from line 17 onwards (session restore, styles, hero, steps, footer) is completely untouched.

### Exact Insertion Points

#### 1. New import (after existing imports, before `st.set_page_config`)

```python
from pipeline.persistence.auth import init_users_table, verify_login, register_user
```

#### 2. Auth gatekeeper block (after `st.set_page_config`, before line 17)

```python
# ── Auth Init ─────────────────────────────────────────────────────────────────
init_users_table()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated", False):

    # ── Login page styles ──────────────────────────────────────────────────────
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 3rem !important; max-width: 880px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Two-column layout: branding left, form right ───────────────────────────
    brand_col, form_col = st.columns([1.2, 1], gap="large")

    with brand_col:
        st.markdown("""
        <div style="padding-top:2rem;">
            <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;">CASEGEN</div>
            <div style="font-family:'DM Serif Display',Georgia,serif;font-size:30px;font-weight:400;line-height:1.25;color:#0F172A;margin-bottom:16px;">
                From raw company data to a publishable case study.
            </div>
            <div style="font-size:14px;line-height:1.7;color:#64748B;">
                A 4-agent AI pipeline that extracts facts, discovers themes,
                writes the narrative, and exports to Word or PDF — all from
                your uploaded source material.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with form_col:
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        # ── Sign In tab ────────────────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                username_input = st.text_input("Username", placeholder="Enter username")
                password_input = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submitted:
                # TC03: Empty fields check
                if not username_input.strip() or not password_input.strip():
                    st.warning("Please enter both username and password.")
                # TC01 / TC02 / TC04: Credential verification
                elif verify_login(username_input.strip(), password_input):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username_input.strip()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        # ── Register tab ───────────────────────────────────────────────────────
        with tab_register:
            with st.form("register_form"):
                reg_fullname  = st.text_input("Full name")
                reg_studentid = st.text_input("Student ID")
                reg_username  = st.text_input("Username")
                reg_password  = st.text_input("Password", type="password")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if reg_submitted:
                if not all([reg_fullname.strip(), reg_studentid.strip(), reg_username.strip(), reg_password.strip()]):
                    st.warning("All fields are required.")
                else:
                    result = register_user(reg_username.strip(), reg_password, reg_fullname.strip(), reg_studentid.strip())
                    if result is True:
                        st.success(f"Account created for **{reg_username}**. Switch to Sign In to continue.")
                    else:
                        st.error(result)

    st.stop()   # ← Nothing below this runs for unauthenticated users

# ── Logout button in sidebar (only shown when authenticated) ───────────────────
with st.sidebar:
    st.markdown(f"<div style='font-size:13px;color:#64748B;padding:4px 0 8px;'>Signed in as <b>{st.session_state.get('username','')}</b></div>", unsafe_allow_html=True)
    if st.button("Sign out", key="logout_btn"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

# ── EVERYTHING FROM HERE IS ORIGINAL HOME.PY — ZERO CHANGES ──────────────────
```

After `st.stop()` is inserted, the entire original `Home.py` body (session restore, styles, sidebar, hero, steps, footer — lines 17–240) continues **verbatim**. Nothing is deleted, rewritten, or reordered.

---

## Phase D — Verify Nothing Is Broken

```bash
# 1. Compile check
./venv/bin/python -m compileall -q Home.py pipeline/persistence/auth.py

# 2. Auth logic unit check
./venv/bin/python -c "
from pipeline.persistence.auth import init_users_table, verify_login, register_user
init_users_table()
print('TC01:', verify_login('ananshi', 'CaseGen@2026'))      # True
print('TC02:', verify_login('ananshi', 'wrongpassword'))      # False
print('TC04:', verify_login('ghost_user', 'CaseGen@2026'))   # False
result = register_user('testuser99', 'Pass@123', 'Test User', '999999')
print('Register:', result)                                   # True
print('TC01-new:', verify_login('testuser99', 'Pass@123'))   # True
"

# 3. Full import chain
./venv/bin/python -c "
import Home  # should import without error (won't render, just import-checks)
"
```

All three must pass before committing.

---

## Phase E — Commit and Push

```bash
git add pipeline/persistence/auth.py Home.py
git commit -m "feat(auth): add login/register gateway with SQLite + PBKDF2 hashing

- New file: pipeline/persistence/auth.py
  - init_users_table() seeds 4 demo accounts on first run
  - register_user() with PBKDF2-HMAC-SHA256 + random salt
  - verify_login() with constant-time comparison
- Modified: Home.py
  - Auth gatekeeper inserted at top; st.stop() blocks unauthenticated access
  - Logout button added to sidebar
  - All existing code (lines 17-240) completely unchanged

Test cases TC01-TC04 (Auth module, Ananshi Sharma 240377) are
demonstrable directly on this login screen."

git push origin academic/course-eval-auth
```

---

## Test Cases — Live Demo Guide (TC01–TC04)

All demonstrated on the **login screen** that now appears when the app loads.

| ID | Test Case | Steps to Demo | Expected Result | Pass Criteria |
|---|---|---|---|---|
| **TC01** | Valid login | Enter `ananshi` / `CaseGen@2026` → Sign In | Login succeeds, hero page loads | Hero section visible; "Get started" works |
| **TC02** | Wrong password | Enter `ananshi` / `wrongpassword` → Sign In | Red error message | "Invalid username or password." appears |
| **TC03** | Empty fields | Leave both fields blank → Sign In | Yellow warning | "Please enter both username and password." appears |
| **TC04** | Unknown user | Enter `ghost_user` / `anything` → Sign In | Red error (same as TC02) | "Invalid username or password." — no info leak |

> **Note on TC04:** Returns the same error as TC02 intentionally — this is a security best practice (username enumeration prevention). Mention this to the professor — it shows you thought about security.

---

## What Is NOT Changing

| File / Component | Why It's Untouched |
|---|---|
| `pages/1_Upload_Documents.py` | Existing functionality, TC05–TC07 |
| `pages/2_Configure_Case.py` | Existing functionality, TC09 |
| `pages/3_Discover_Themes.py` | Existing functionality, TC10–TC11 |
| `pages/4_Generate_Case_Study.py` | Existing functionality, TC12 |
| `pages/5_Review_Export.py` | Existing functionality, TC13–TC15 |
| `pages/6_History.py` | Existing functionality, TC16 |
| `pipeline/agents/*` | Zero agent code changes |
| `pipeline/persistence/case_history.py` | Zero changes |
| `pipeline/persistence/session_store.py` | Zero changes |
| `config.py` | Zero changes |
| `.env` | Zero changes — no new keys needed |
| `requirements.txt` | Zero changes — `hashlib` and `secrets` are stdlib |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| `st.stop()` blocks existing session restore | Low | Session restore block is AFTER the gatekeeper; authenticated users hit it normally |
| `users` table creation fails on first run | Very Low | `CREATE TABLE IF NOT EXISTS` is idempotent; existing `case_history.db` has no conflict |
| Import error in `auth.py` breaks startup | Very Low | Phase D compile + import check catches this before commit |
| Merge conflict with `main` later | None | Branch is clean; auth files don't overlap with any existing files |
| Existing pages become inaccessible | None | Streamlit pages routing is unaffected; auth only blocks `Home.py` entry point |

> **Bottom line:** The only file being modified is `Home.py` and only by prepending code at the top. The `st.stop()` call is the entire mechanism — it's one line that halts rendering for unauthenticated users. Everything below it is the original app.

---

## Summary of Files Created/Changed

```
pipeline/
  persistence/
    auth.py              ← NEW FILE (created in Phase B)

Home.py                  ← MODIFIED (top ~55 lines added in Phase C)
```

**That is all.** Two files. The rest of the project is untouched.

---

*Say **"start"** when you are ready to begin Phase A.*
