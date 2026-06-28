**AI-Powered Case Study Generator**

**Complete Technical Explanation Document**

Date: 19 June, Version 2

**Table of Content**

| **S no.** | **Item**                                   | **Page no.** |
| --------- | ------------------------------------------ | ------------ |
| **1**     | **Introduction and Core Objective**        | **2**        |
| **2**     | **System Overview**                        | **3**        |
| **3**     | **Complete Project Walkthrough**           | **4**        |
| **4**     | **The 4-Agent Pipeline**                   | **14**       |
| **5**     | **Data Flow and Session State Management** | **15**       |
| **6**     | **Quality Assurance Layers**               | **16**       |
| **7**     | **Gaps and Fixes**                         | **16**       |
| **8**     | **Quote Extraction from Audio Files**      | **17**       |
| **9**     | **Technical Summary Table**                | **18**       |
| **10**    | **Conclusion**                             | **19**       |

**Introduction and Core Objective**

**Problem we solve**

Writing a high-quality business case study often takes weeks or even months of manual effort. Analysts need to collect and review information for multiple sources such as annual reports, interview recordings, presentations, spreadsheets, etc., before they can develop a complete accurate case study.

Generic AI tools such as ChatGPT can struggle with this process because they may hallucinate and generate inaccurate information when working with large volumes of mixed data. This can lead to fabricated financial figures, incorrect dates or even events that never occurred, thus reducing the reliability of the final case study.

**Core Objective**

To build an AI powered Web Application that automates Case Study generation while ensuring factual accuracy. The system can process messy real world data, like scanned PDFs, audio recordings, spreadsheets and URLs, and output a structured Standard Case study.

**How do we mitigate Hallucinations?**

We use a 4-Agent Pipeline that strictly separates factual extraction from creative writing, combined with factual verification check (truth integrity), Pydantic validation (structural integrity and a manual review/ adjustment editor.

**System Overview**

The application is a **Streamlit** Web App running locally on device.  
It consists of 5 screens through which one can navigate by clicking on "BACK" and "NEXT" buttons. This also ensures no steps are skipped.

| Page | File Name                | User Action                                                                                                             |
| ---- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| 1    | 1_Upload_Docs.py         | Drag and drop files(PDF, audio, Excel, URL). Click NEXT                                                                 |
| 2    | 2_Config_CaseStudy.py    | Select tone, audience, purpose, theme, privacy, citation format. Click NEXT                                             |
| 3    | 3_Analyse_SelectAngle.py | Watch progress bar spin as Agent 1 extracts facts. Then pick which theme(eg HR vs Supply Chain) to focus on. Click NEXT |
| 4    | 4_Generate_CaseStudy.py  | New progress bar spins as Agent 2, 3 & 4 write and fact check. Click NEXT                                               |
| 5    | 5_Edit_Export.py         | Review final text, edit the case study manually if required, then download as word or pdf.                              |

The workflow of the above is as follows:

- **Upload:** The user uploads files on Page 1, where all data is extracted locally before proceeding to the next step.
- **Configure:** The user configures the required settings and inputs on Page 2 and then clicks Next.
- **Chunk:** The system automatically divides the extracted content into 1,000 token chunks in the background.
- **Agent 1:** It extracts facts, identifies key themes, and generates a structured FactSheet.
- **Theme Selection:** The user reviews the discovered themes on Page 3, selects a preferred case study theme, and clicks Next.
- **Agents 2 and 3:** On Page 4, the second and third agents simultaneously generate the case study narrative and supporting exhibits.
- **Agent 4:** The final agent performs editing, fact checking, bias detection, privacy masking, and citation generation.
- **Edit and Export**: On Page 5, the user reviews and edits the final case study before exporting it in the desired format.

All intermediate data will live in **st.session_state** (with local JSON backup to survive browser refresh)

**Complete Walkthrough**

**Step 1: Upload Document (Page 1)**

**What user sees**

- A drag and drop area labeled as "Upload source files" will be displayed on the first page.
- User can upload, for example, a 60 page annual report pdf, a 25 min interview mp3, an excel file of financial data and/ or a URL to an article online.
- After each successful upload, a green checkmark will appear next to the corresponding file name.
- User clicks on the NEXT button at the bottom of the page to continue to the next step.

**Behind the scene**

**PDF:**

- IBM Docling extracts text while preserving document structure.
- OCR processes scanned pages automatically.
- Tables are converted into clean Markdown format.
- Extracted content is tagged with source filename and page number.

**Error handling for Corrupted or Password protected PDFs:**

- Extraction runs inside a try/ except block
- Clean error messages are shown for corrupted or password protected files.
- The workflow pauses until all files are processed successfully.

**Audio (MP3, MP4, M4A,WAV, MPEG, MPGA and WEBM):**

- Open AI Whisper runs locally on the device.
- User can choose from tiny (fastest), base (balanced), small (accurate), medium ( recommended for Indian English), large (most accurate, take 45+ minutes for 30 minute recording)
- Voice activity detection removes silence and background noise.
- Audio is transcribed in chunks and tagged with the source file name.

**Timeout Handling:**

- Transcription runs in a background thread.
- A progress spinner displays estimated completion time.
- User can continue working while transcription runs.
- Completed transcripts are stored in st.session_state\['master_transcript'\].

**Excel/ CSV files:**

- Pandas loads the spreadsheet data.
- Dataframes are converted into markdown tables.
- Rows, columns and numeric formatting are preserved.
- Extracted data is tagged with the source filename.

**Web URL:**

- Beautifulsoup extracts webpage content.
- Script and Styles elements are removed automatically.
- Plain text is tagged with the source URL.

All extracted text from all sources is merged into a single python dictionary called Master Transcript, keyed by source file name. This is stored in st.session_state\['master_transcript'\].

**Step 2: Configure Case Study (Page 2)**

**What user sees**

- A configuration panel with 8 inputs (dropdown, toggle and text fields).
- User clicks on the NEXT button at the bottom of the page to continue to the next step.

User selects the following:

- **Output Purpose**
  - **UI Element:** Dropdown Menu
  - **Options to select from:**
    - IFQM Teaching Case (Standard academic format)
    - Corporate Post-Mortem (Internal lessons learnt report)
    - Investor Memo (Financial and risk heavy brief)
    - B2B Marketing Story (Success story for client)
    - Executive Summary (Short, bullet point heavy)
- **Business Discipline**
  - **UI Element:** Dropdown Menu
  - **Options to select from:**
    - Strategy
    - Operations
    - HR
    - Brand and marketing
    - Supply chain
    - Quality
    - Finance and Accounting
- **Tone of Voice**
  - **UI Element:** Dropdown Menu
  - **Options to select from:**
    - Optimistic and Journalistic (Neutral, facts only)
    - Highly Critical and Diagnostic (Focuses heavily on flaws and mistakes.)
    - Persuasive and Visionary (Inspiring and forward looking)
- **Target Audience**
  - **UI Element:** Dropdown Menu
  - **Options to select from:**
    - Undergraduate/ BBA (simpler vocabulary, explains business concepts)
    - Graduate/ MBA (Standard Harvard/ IFQM case level)
    - C-Suite Executives (Highly Strategic)
    - General Public (Accessible to non-business readers)
- **Theme**
  - **UI Element:** Short Text Input Box
  - **Options:**
    - None, user types freely.  
       E.g., "Sustainability, Digital Transformation"
- **Custom Instructions**
  - **UI Element:** Large Text Input Box
  - **Options:**
    - None, user types freely.  
       E.g., "Make sure to heavily emphasize CEO Ratan Tata's leadership style during the 2008 crisis"
- **Data Privacy Masking**
  - **UI Element:** Toggle Switch
  - **Options:**
    - **ON:** Scrub financial numbers and replace them with percentage trends. (to protect company secrets)
    - **OFF:** Use the exact raw numbers found in data uploaded.
- **Citation Format**
  - **UI Element:** Dropdown Menu
  - [**Options to select from**](http://pitt.libguides.com/citationhelp)**:**
    - **APA (7th edition):** focuses on Author and publication year**For:** Business, management, psychology,**  
       In-text citation example**: (Tata Motors Ltd., 2024)  
       **Reference list example:** Tata Motors Ltd. (2024). _Annual report 2023-2024._ <https://www.tatamotors.com>
    - **MLA (9th edition):** focuses on Author and publication year**For:** Literature, humanities, language studies**  
       In-text citation example**: (Tata Motors 34)  
       **Reference list example:** Tata Motors Ltd. _Annual report 2023-2024._ (2024), <https://www.tatamotors.com>
    - **Chicago (17th edition):** Uses footnotes or endnotes. (Notes and Bibliography)**For:** History, publishing, some business programs**  
       In-text citation example**: ¹ (superscript footnote number)  
       **Footnote example:** ¹Tata Motors Ltd., _Annual Report 2023-24_ (Mumbai: Tata Motors, 2024), 34.
    - **IFQM Custom:  
       In-text citation example**: \[Source: Tata_AR_2024.pdf, p. 34\]  
       **Reference list example:** Tata Motors Ltd. (2024). Annual Report 2023-24, p. 34. Retrieved from company records.

**APA (7th Edition) is selected by default.**

We will use a combination of both, in-text citations and references list, but with a strong emphasis on references list at the end. To keep the document looking highly professional, we will instruct the Agents to do the following:

In-Text Citations: Agent 2 will only use in-text citations if it is a direct quote from a person.  
Example: _"We had to completely restructure our supply chain", said CEO Ratan Tata (Source: CFO_Interview.mp3)_

Reference List: Agent 4 will compile a numbered reference list for everything else (e.g., revenue numbers, dates) at the very end of the document.

**Step 3: Chunking (in background)**

This step happens automatically after the user leaves page 2 but before page 3 loads. The user sees a spinner saying "Preparing your documents for analysis".

**What happens behind the scene:**

The Master transcript may exceed 100k tokens which are too large to send to LLM in one API call. We use LangChain's **RecursiveCharachterTextSplitter** to split the transcript into chunks of exactly 1k tokens( approx 750 words). We set an overlap of 200 tokens between adjacent chunks which ensures that a sentence split across two chunks does not lose its semantic meaning. Each chunk retains the source metadata of its original text.  
The resulting list of chunks is stored in st.session_state\['chunks'\].

**Handling Context Window Overflow:**

If the total number of chunks still exceeds Gemini's context window(e.g., 200 chunks), we do not send all chunks at once. Instead, Agent 1 processes chunks in batches of 10-15 at a time, thus producing a particle Fact Sheet per batch. A merge step then deduplicates and combines all partial FactSheets into 1 final FactSheet. This logic will be implemented in _pipeline/agents/agent_extrcator.py_.  
After chunking completes, page 3 loads automatically (no user click required).

**Step 4: Agent 1, Fact extraction and Theme Discovery (page 3, fist half)**

**What the user sees on page 3**

Before any theme selection, a progress bar on page 3: "Agent 1 is reading your documents and extracting facts"

**What happens behind the screen?**

We call Google Gemini API. Agent 1's system prompt will be strictly objective:  
"You are a fact extractor. Read the provided text chunks. Extract every hard fact: dates, financial figures, people's names, quotes, challenges, outcomes. Group the facts into distinct narrative themes (e.g., 'Supply Chain Crisis', 'HR Culture Crisis'). Do not editorialise. Do not apply any tone. Output only valid JSON according to the provided Pydantic schema."

**Batch processing and merging:**

We send chunks in batches of 10-15. For each batch, Agent 1 returns a particle Fact Sheet(a JSON object with fields like company_name, founding_year, revenue, timeline_events, themes\[\]).

After all batches are processed, a merge function does the following:

- Deduplicates identical facts (e.g., same revenue figure from two chunks)
- Combines facts from different batches into a single JSON structure.
- Preserves source metadata for every fact(used later for citations).

**Pydantic validation along with auto retry:**

- A strict Pydantic Schema is defined to enforce the expected structure and datatypes of the generated output:
  - revenue: float
  - founding year: integer
  - themes: list\[str\]
- The application sends a prompt to Gemini requesting JSON response that matches the schema exactly.
- If Gemini returns malformed or invalid JSON(missing commas, incorrect datatypes, missing fields), Pydatic raises a **ValidationError.**
- The validation error details are appended to the original prompt along with correction instructions such as "You made a JSON syntax or schema error. Fix it and return a valid JSON object"
- The corrected prompt is resent to Gemini automatically.
- The auto retry loop runs for up to 3 attempts, ensuring the output conforms to the required schema.
- Once a validation succeeds, the final structured response is stored in the following manner:
  - St.session_state\['fact_sheet'\] : complete validation Fact Sheet object
  - St.session_state\['themes'\]: extracted list of themes
- This approach ensures the following:
  - Consistent JSON formatting
  - Strict type safety
  - Reduced manual error handling
  - Reliable downstream processing and UI rendering

**Step 5: Angle Selection**

**What the user sees (after Agent 1 finishes):**

- The pipeline pauses after Agent 1 completes its analysis. When it extracts facts, it also attaches "theme tag" to every single one.  
   _Example: Fact 1: Shipping costs rose 400% \[Tag: Supply Chain\]_
- The screen displays: "Document analysed and found 3 major themes. Which angle should case study focus on?"
- Interactive buttons are shown for each identified theme (e.g., supply chain crisis, HR culture crisis, debt restructuring).
- After selecting the theme, the user clicks on the NEXT button.

**What happens behind the scenes:**

- Streamlit pauses further execution using button widgets, no additional AI calls are made during this stage.
- Once a theme is selected, The backend creates a **filtered_factsheet** containing only the facts associated with the chosen theme.
- Fats related to other themes are temporarily executed to ensure Agent 2 and 3 focus on a single coherent narrative.
- The filtered data is stored in st.session_state\['filtered_fact_sheet'\]
- When the user clicks on NEXT, it navigates to page 4 (pages/4_Generate_CaseStudy.py). A BACK button on page 3 allows users to return to page 2 and update their configuration setting.

**Step 6: Parallel Generation: Agent 2 & Agent 3 (Page 4)**

**What the user sees:**

Page 4 shows a progress bar with two simultaneous indicators: "Agent 2 is writing the narrative…" and "Agent 3 is building the exhibits…" When both finish, a "NEXT" button appears. A "BACK" button returns to Page 3 to select a different angle.

**What happens behind the scenes:**

Using Python's threading module, we run two separate API calls to Gemini in parallel.

**Agent 2 (Storyteller):**

- Inputs:
  - Filtered FactSheet (st.session_state\['filtered_fact_sheet'\])
  - UI config: Tone, Audience, Core Theme, Custom Instructions, Business Discipline
  - t**emplates/case_template.json** defines required sections (Background, Industry Context, Challenge, Intervention, Results, Learnings) and word limits (min 400, max 1200 per section).
  - **templates/few_shot_examples.json** contains 2 perfect example paragraphs for each section, taken from real published case studies (from 18 cases analysed).
- System prompt:
  - "You are a case study storyteller. Write flowing prose for the required sections. Use the provided FactSheet only. Do not invent any number or fact not in the FactSheet. Follow the template structure exactly. Mimic the tone and vocabulary from the few‑shot examples."
- Output: Markdown text for Background, Industry Context, Challenge, Intervention, Results, Learning Outcomes.

**Agent 3 (Analyst):**

- Inputs:
  - Filtered Fact Sheet
  - UI config: Audience (only)
- System prompt:
  - "You are a case study analyst. Generate exhibits as Markdown tables (financial comparisons, KPI before/after) and discussion questions. If Audience = Undergraduate, generate 3 comprehension‑level questions. If Audience = MBA/C‑Suite, generate 5 complex strategic synthesis questions. Do not invent numbers."
- Output: Markdown tables for Exhibits section and list of Discussion Questions.

Both outputs are stored separately in st.session_state\['narrative'\] and st.session_state\['exhibits'\].

**Section level regeneration:**

The architecture includes a function regenerate_section(section_name, factsheet, ui_config) that calls Agent 2 again for only one section (e.g., "Challenge") while keeping the rest unchanged. This is exposed on Page 5 as a "Regenerate this section" button next to each section heading.

When generation finishes, the "NEXT" button appears. Clicking it switches to pages/5_Edit_Export.py.

**Step 7: Agent 4 (Editor, Fact‑Checker, Bias Detector, Privacy Masker, Citation Generator)**

Agent 4 runs automatically as soon as Page 5 loads, the user sees a brief progress message: "Agent 4 is fact checking and formatting the final document…" before the editable text area appears.

**What happens behind the scenes:**

Agent 4 receives:

- Agent 2's narrative (st.session_state\['narrative'\])
- Agent 3's exhibits (st.session_state\['exhibits'\])
- The original (unfiltered) Fact Sheet (st.session_state\['fact_sheet'\]) used for cross checking all facts, not just filtered ones.
- UI config: Output Purpose, Data Privacy toggle, Citation Format.

It performs five sequential operations:

- **Merge:** Combines narrative and exhibits into a single Markdown document in the correct section order: Title, Background, Industry Context, Challenge, Intervention, Results, Exhibits, Discussion Questions, References.
- **Factual Verification Check:** Scans every number and date in the narrative. For each figure, it checks whether that exact figure exists anywhere in the original Fact Sheet. If not, the sentence containing the figure is flagged and rewritten to remove the unverified claim. Example: If Agent 2 wrote "Revenue reached ₹4.38 lakh crore in 2024" but the FactSheet only contains revenue for 2023, Agent 4 deletes the sentence or replaces it with a verified statement.
- **Bias detection (quality layer):** A specialised prompt checks the final narrative for promotional language:  
   "Analyze this text for promotional bias. If the text uses unsupported superlatives (e.g., 'the best company', 'revolutionary product') without quantitative data from the FactSheet, suggest neutral rephrasings."  
   Agent 4 then rewrites any biased sentences to neutral academic language.
- **Data privacy masking:** If the user toggled **Data Privacy = ON**, Agent 4 replaces all exact financial figures with directional language (not fabricated percentages). For example:
  - "Profit was ₹2.1 crore" into "Profit increased significantly during this period."
  - "Revenue of ₹50,000 crore" into "Revenue grew substantially."
  - If the FactSheet already contains a percentage change (e.g., "revenue grew by 15%"), that percentage is kept. Only absolute numbers are masked.

Note: We will not use regex to fabricate percentages, as that would be misleading.

- **Citation engine:** Agent 4 compiles all source metadata tags attached to each fact in the FactSheet. It then generates a "References" section at the end of the document in the selected Citation Format (APA, MLA, Chicago, or IFQM custom). Each reference includes the source filename, page number (if available), and URL (if web source).

The final, complete Markdown document is stored in st.session_state\['final_markdown'\] and displayed in the editable text area on Page 5.

**Step 8: Human Review & Export (Page 5)**

**What the user sees:**

The complete case study appears inside a large editable text area (Streamlit's st.text_area). The user reads through the text, changes sentences, fixes typing errors or adjusts tables. Next to each section heading, there is a "Regenerate this section" button (implements the section level regeneration feature).

At the bottom of the page: "BACK" (returns to Page 4 to regenerate with the same settings) and "Download as Word (.docx)" and "Download as PDF" buttons. No "NEXT" button as this is the final page.

**What happens behind the scenes:**

- **Word export:** We use the python docx library. It takes the final **Markdown** string and converts as follows:
- \# Heading 1: Word "Heading 1" style.
- \## Heading 2: Word "Heading 2" style.
- \*\*bold\*\*: bold text.
- Markdown pipe tables (| col1 | col2 |): native Word table objects.
- Margins and fonts are set to match IFQM standards from the Standard Template (e.g., Times New Roman, 12pt, 1-inch margins).
- The resulting .docx file is served via st.download_button.
- **PDF export:** We convert the Markdown to HTML (using a simple Markdown‑to‑HTML converter) and then generate a PDF using WeasyPrint (a free, local HTML‑to‑PDF engine). The PDF preserves all formatting, tables, and fonts.
- **Session persistence (gap fix):** After generation, the system saves the final Markdown and the FactSheet to a local output/ folder with a timestamp. If the user refreshes the browser, the app checks for existing saved sessions and offers to restore thus preventing loss of work.
- All generated case studies are also saved to a local SQLite database (case_history.db) with timestamps, allowing users to revisit past work. A separate "My Case Studies" page (accessible from the sidebar) lists all previously generated cases.

**The 4‑Agent Pipeline**

**Agent 1: Fact Extractor**

- Inputs: Chunked Master Transcript (batches of 10-15 chunks).
- Outputs: Pydantic‑validated FactSheet JSON + list of discovered themes.
- Does NOT receive: Any UI configuration (tone, audience, etc.).
- Retry logic: Up to 3 auto‑retries on JSON validation errors.
- Runs: Sequentially after chunking, before angle selection (Page 3).

**Agent 2: Storyteller**

- **Inputs:** Filtered Fact Sheet, UI config (Tone, Audience, Theme, Custom, Discipline), case_template.json , few_shot_examples.json.
- **Outputs:** Markdown prose for Background, Industry Context, Challenge, Intervention, Results, Learnings.
- **Prohibited from:** Inventing any number not in the Fact Sheet.
- **Runs:** In parallel with Agent 3 on Page 4.

**Agent 3: Analyst**

- **Inputs:** Filtered FactSheet, UI config (Audience only).
- **Outputs:** Markdown exhibits (tables) + Discussion Questions.
- **Prohibited from:** Writing narrative prose.
- **Runs**: In parallel with Agent 2 on Page 4.

**Agent 4: Editor & Verifier**

- **Inputs:** Agent 2 output, Agent 3 output, original FactSheet, UI config (Purpose, Privacy, Citation Format).
- **Operations:** Merge, factual verification check, bias detection, privacy masking, citation generation.
- **Outputs:** Final Markdown case study (editable on Page 5).
- **Runs:** After Agents 2 and 3 complete, triggered when Page 5 loads.

**Data Flow and Session State Management**

What lives in **st.session_state**:

- Master_transcript: dictionary of all extracted text, keyed by source filename.
- Chunks: list of text chunks after LangChain splitting.
- Fact_sheet: validated Pydantic FactSheet JSON from Agent 1.
- Themes: list of discovered narrative themes.
- Selected_theme: theme user picked on angle selection page.
- Filtered_factsheet: FactSheet filtered to selected theme only.
- Ui_config: dictionary of all UI inputs.
- Narrative: Agent 2 output (prose).
- Exhibits: Agent 3 output (tables/questions).
- Final_markdown: Agent 4 output, editable by user.

**Persistence against browser refresh:**

After Agent 1 completes, we save fact*sheet to output/fact_sheet*\[timestamp\].json. After Agent 4 completes, we save final*markdown to output/case*\[timestamp\].md. On app load, the system checks for recent files and offers to restore the session, preventing loss of work.

All generated case studies are also saved to a local SQLite database (case_history.db) with timestamps, allowing users to revisit past work. A separate "My Case Studies" page lists all previously generated cases.

**Quality Assurance Layers**

We implement five independent quality controls (5 layers):

- **Pydantic validation with auto retry:** Agent 1's output must conform to a strict schema otherwise, Gemini is forced to fix it (up to 3 retries).
- **Factual verification check (Agent 4):** Every number/ date in the narrative is cross checked against the original Fact Sheet. Unverified claims are removed.
- **Bias detection prompt:** Agent 4 scans for promotional language (e.g., "best company", "revolutionary") and rewrites it neutrally. A banned words list (built from analysed cases) is also applied.
- **Manual editor:** The user sees the full case study on Page 5 before downloading and can make any final corrections. No output is final without human approval.
- **Automated self correction on API errors:** If any Gemini API call fails (rate limit, timeout, malformed response), the system retries up to 3 times with exponential backoff.

**Gaps and Fixes**

| **Gap**                                                         | **Fix**                                                                                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| No error handling for corrupted/ password protected PDFs        | try/except around Docling; user friendly error message; pipeline halts until fixed.                                      |
| Whisper takes too long with no timeout or background processing | Background thread with spinner; user can continue to Page 2; estimated time shown.                                       |
| Context window overflow not fully handled                       | Batch processing of chunks (10-15 per API call); merge partial Fact Sheets.                                              |
| Session state lost on browser refresh                           | Save FactSheet and final Markdown to local JSON/MD files; restore on load.                                               |
| Data privacy masking described as regex but not implementable   | Use directional language ("increased significantly") instead of fabricated percentages.                                  |
| No user accounts or saved history                               | SQLite database stores all generated cases; "My Case Studies" page.                                                      |
| Section level regeneration mentioned but not defined            | regenerate_section() function calls Agent 2 for only one section; UI button on Page 5.                                   |
| Citation format unspecified                                     | Added Citation Format dropdown (APA, MLA, Chicago, IFQM) routed to Agent 4.                                              |
| Whisper model size not specified                                | Added settings panel for model selection (tiny/base/small/medium/large) with recommendation for Indian English (medium). |

**Quote Extraction from Audio Files**

**The challenge:**

PDFs have quotation marks (""), but raw audio transcripts from Whisper have no punctuation. People don't speak in quotes.

**How does Agent 1 solve it (without code)?**

**Structured Quote Catcher:** Agent 1's output schema includes a dedicated field called key_quotes. The AI knows it must fill this field with impactful leadership statements.

**Semantic understanding (Gemini 1.5):** The AI reads the transcript and understands context, not punctuation. It can identify when someone is directly stating an opinion or describing a critical event.

**System prompt instructions** where Agent 1 is told to do the following:

- Find the 3-5 most impactful statements made by leadership (CEO, CFO, founders).
- Clean up filler words like "um", "ah", and repeated words.
- Record the speaker name and source file for each quote.

Example:

**Messy transcript:** CEO Ratan Tata: Honestly it was the hardest thing we ever faced, our entire supply chain froze overnight.

**Extracted quote:** "Honestly it was the hardest thing we ever faced, our entire supply chain froze overnight." -CEO Ratan Tata (Audio_Interview.mp3)

**How do quotes reach the final case study?**

Agent 1 passes the key_quotes list to Agent 2 (Storyteller).

Agent 2 naturally weaves the best quotes into the narrative paragraphs.

Final output example:

_CEO Ratan Tata later reflected, "Honestly it was the hardest thing we ever faced…"_

**Quality checks:**

- Filler words are automatically removed.
- The speaker is identified from labels (e.g., "CEO:") or inferred from context.
- Agent 4's fact checking does not remove quotes, it only verifies numbers inside quotes (e.g., "300% growth" is checked against the FactSheet).

Summary: Agent 1 uses a dedicated key_quotes field and semantic understanding to extract quotes from messy audio. Agent 2 then injects those quotes into the case study for drama and credibility.

**Technical Summary Table (All Components)**

| **Component**       | **Technology**                             | **Role**                                                             | **Key Detail**                                                   |
| ------------------- | ------------------------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Frontend UI         | Streamlit                                  | 5‑page wizard with Next/Back buttons                                 | st.switch_page() for navigation                                  |
| PDF text & OCR      | IBM Docling                                | extracts text and tables from PDFs, applies OCR to scanned pages     | Preserves financial tables as Markdown                           |
| Audio transcription | OpenAI Whisper                             | Converts MP3/WAV to text, runs on CPU                                | Model size selectable (tiny to large)<br><br>Spreadsheet parsing |
| Spreadsheet parsing | Pandas                                     | Converts Excel/CSV to Markdown tables                                | df.to_markdown()                                                 |
| Web scraping        | BeautifulSoup                              | Extracts text from URLs                                              | Removes script/style tags                                        |
| Text chunking       | LangChain (RecursiveCharacterTextSplitter) | Splits large transcripts into 1k token chunks with 200 token overlap | Prevents lost‑in‑the‑middle                                      |
| AI                  | Google Gemini API (free tier)              | Powers all 4 agents                                                  | Free (60 req/min)<br><br>Model: gemini-1.5-flash                 |
| Data validation     | Pydantic                                   | Enforces strict JSON schema, auto‑retry on errors                    | Up to 3 retries                                                  |
| Word export         | python‑docx                                | Converts Markdown to formatted .docx                                 | IFQM margins & fonts                                             |
| PDF export          | WeasyPrint                                 | Converts HTML to PDF                                                 | HTML intermediate step                                           |
| Session persistence | SON and SQLite                             | Saves FactSheet and case studies for recovery/ history               | Built‑in Python libraries                                        |
| Threading           | Python threading                           | Runs Whisper and Agents 2&3 in background                            | Improves user experience                                         |

**Conclusion**

The AI Powered Case Study Generator is a 100% free, local, hallucination‑free application that transforms messy company data into professional teaching case studies in minutes. The user is guided through a 5‑page application with clear NEXT and BACK buttons, ensuring no step is missed. By implementing a 4‑Agent Pipeline with strict separation of concerns, Pydantic validation with auto retry, anti‑hallucination and bias detection sweeps, batch chunking to handle context limits, background processing for long audio, session persistence to survive browser refreshes, section‑level regeneration, and comprehensive error handling, the system addresses every gap identified in the initial design.

This tool enables a user to produce a much larger volume of high‑quality Indian business case studies while guaranteeing factual accuracy and academic integrity.