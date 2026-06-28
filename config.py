import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get the API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing from the .env file!")

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