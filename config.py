import os
import sys
from dotenv import load_dotenv

# Ensure stdout/stderr can emit non-ASCII (₹, em-dashes, accented names) on
# Windows consoles that default to cp1252 — otherwise agent prints crash the run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load the .env file
load_dotenv()

# LLM provider: "gemini" (default) or "openrouter"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Get the API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing from the .env file!")
if LLM_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
    raise ValueError("CRITICAL ERROR: OPENROUTER_API_KEY is missing from the .env file!")

#Metadata (Title & Abstract) 
CASE_METADATA = {
    "title_required": True,
    "title_min_words": 2,
    "title_max_words": 8,
    "company_name_in_title": True,
    "abstract_required": False,
    "abstract_word_count_min": 100,
    "abstract_word_count_max": 150,
}

# Exhibits Configuration
EXHIBITS_CONFIG = {
    "required": False,
    "min_count": 2, # aim for at least 2 if data available
    "max_count": 6,
    "types": ["financial_table", "market_share_chart", "timeline_diagram", "process_flow"],
    "source_restriction": "Use ONLY data from the Fact Sheet. Do not invent numbers.",
    "skip_if_no_data": True,# if Fact Sheet (by agent 1) lacks numeric data, skip exhibits entirely
}

#File Paths
TEMPLATE_PATH = "templates/case_template.json"
FEW_SHOT_PATH = "templates/few_shot_examples.json"

#Model Settings
GEMINI_MODEL = "gemini-2.0-flash"
WHISPER_MODEL = "base"
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300
LLM_TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 8192