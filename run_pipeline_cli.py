import os
import json
from datetime import datetime
from pipeline.ingest.fast_pdf_parser import parse_pdf_fast
from pipeline.ingest.spreadsheet_parser import parse_spreadsheet
from pipeline.ingest.text_chunker import chunk_master_transcript
from pipeline.agents.agent_extractor import run_agent_1
from pipeline.agents.run_generation import run_generation


# 1. Parse documents
print("Parsing documents...")
master_transcript = {}

with open('sample_input/toyota_1.pdf', 'rb') as f:
    import io
    pdf_obj = io.BytesIO(f.read())
    pdf_obj.name = 'toyota_1.pdf'
    pdf_text = parse_pdf_fast(pdf_obj)
    master_transcript['toyota_1.pdf'] = pdf_text

with open('sample_input/production_sales_figures_en_202605.xlsx', 'rb') as f:
    import io
    excel_obj = io.BytesIO(f.read())
    excel_obj.name = 'production_sales_figures_en_202605.xlsx'
    excel_text = parse_spreadsheet(excel_obj)
    master_transcript['production_sales_figures_en_202605.xlsx'] = excel_text

# 2. Chunking
print("Chunking...")
chunks = chunk_master_transcript(master_transcript)
print(f"Total chunks: {len(chunks)}")

# 3. Agent 1
print("Running Agent 1 (Extractor)...")
fact_sheet = run_agent_1(chunks, batch_size=10)

# Save fact sheet
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
fs_path = f"output/fact_sheet_{timestamp}.json"
os.makedirs("output", exist_ok=True)
with open(fs_path, "w", encoding="utf-8") as f:
    json.dump(fact_sheet.model_dump(), f, indent=2, ensure_ascii=False)
print(f"Fact sheet saved to {fs_path}")

# 4. Agent 2 & 3
print("Running Agents 2 & 3 (Storyteller & Analyst)...")
ui_config = {
    "purpose": "Academic instruction",
    "discipline": "Business Strategy",
    "tone": "Neutral, analytical",
    "audience": "MBA students",
    "selected_theme": fact_sheet.themes[0] if fact_sheet.themes else "General Business Analysis",
    "custom_instructions": ""
}

result = run_generation(fact_sheet, ui_config)

# 5. Assemble Markdown
print("Assembling case study...")
parts = []
parts.append(f"# {fact_sheet.company_name} Case Study\n")
parts.append(f"**Theme**: {ui_config['selected_theme']}\n\n")

for section_id in ["background", "industry_context", "challenge", "intervention", "results", "learnings"]:
    if section_id in result["narrative"]:
        parts.append(result["narrative"][section_id])
        parts.append("\n\n")

if result.get("exhibits"):
    parts.append("## Exhibits\n\n")
    parts.append(result["exhibits"])
    parts.append("\n\n")

if result.get("discussion_questions"):
    parts.append("## Discussion Questions\n\n")
    for idx, q in enumerate(result["discussion_questions"]):
        parts.append(f"{idx+1}. {q}\n")

final_markdown = "".join(parts)

case_path = f"output/case_{fact_sheet.company_name.replace(' ', '_')}_{timestamp}.md"
with open(case_path, "w", encoding="utf-8") as f:
    f.write(final_markdown)

print(f"Case study successfully generated and saved to {case_path}")
