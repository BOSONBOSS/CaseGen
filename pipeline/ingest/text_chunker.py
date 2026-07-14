# Old implementation preserved as comments for reference
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# def chunk_master_transcript(master_transcript, chunk_size=1000, chunk_overlap=200):
#     combined_text = ""
#     if isinstance(master_transcript, dict):
#         for filename, text in master_transcript.items():
#             if text and text.strip():
#                 combined_text += f"\n\n[Source: {filename}]\n{text}"
#     splitter = RecursiveCharacterTextSplitter(...)
#     chunks = splitter.split_text(combined_text)
#     return chunks

from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

# File patterns that identify a historical/conceptual reference (not a current financial report).
# Any file whose name matches these patterns will be tagged HISTORICAL_REFERENCE_ONLY,
# preventing the LLM from treating its financial figures as current data.
_HISTORICAL_BOOK_PATTERNS = re.compile(
    r"("
    # Toyota-specific management books
    r"production.system|tps|lean.thinking|machine.that.changed|toyota.way|kaizen|monozukuri|gemba"
    # Generic historical/conceptual book title patterns
    r"|the.making.of|history.of|story.of|origin.of|biography|memoir|chronicle"
    r"|management.classic|business.classic|case.study.book|textbook|handbook"
    r"|how.to|principles.of|art.of|science.of|philosophy.of"
    r")",
    re.IGNORECASE,
)

_SPREADSHEET_EXTENSIONS = (".xlsx", ".xls", ".csv")

_REPORT_PATTERNS = re.compile(
    r"(annual.report|integrated.report|sustainability|investor|financial.results|earnings)",
    re.IGNORECASE,
)


def _classify_source(filename: str) -> str:
    """
    Returns a source authority label that the LLM uses to determine how to treat figures
    from a given file. This is the primary defence against cross-source contamination
    (e.g. a 1978 book figure being used as a 2023 revenue number).
    """
    fn = filename.lower()
    if any(fn.endswith(ext) for ext in _SPREADSHEET_EXTENSIONS):
        return (
            "AUTHORITATIVE_DATA: Quantitative spreadsheet / sales data. "
            "All numerical figures here are primary source facts and should be extracted exactly."
        )
    if _HISTORICAL_BOOK_PATTERNS.search(fn):
        return (
            "HISTORICAL_REFERENCE_ONLY: This is a book or academic text describing historical "
            "practices or past context. ANY financial figures (revenue, costs, profits) in this "
            "source reflect the era when the book was written, NOT current financial performance. "
            "DO NOT extract figures from this source as current revenue, profit, or market data. "
            "Use this source ONLY for conceptual frameworks, management philosophy, and historical context."
        )
    if _REPORT_PATTERNS.search(fn):
        return (
            "AUTHORITATIVE_REPORT: Current corporate report. "
            "Financial and strategic figures are current and authoritative."
        )
    return (
        "SUPPORTING_SOURCE: Use for qualitative context only. "
        "Do not treat financial figures from this source as current company performance data "
        "unless they are explicitly dated and match the report year."
    )


def _is_boilerplate(chunk: str) -> bool:
    """
    Detects if a chunk is purely legal jargon, table of contents, or accounting boilerplate.
    Filtering these out saves API calls and prevents the LLM from getting distracted by
    legal definitions or index numbers.
    """
    text = chunk.lower()
    
    # 1. Extremely short chunks (usually just page numbers or stray formatting)
    if len(text.strip()) < 50:
        return True
        
    # 2. Dense legal/safe-harbor disclaimers
    if "forward-looking statements" in text and ("safe harbor" in text or "disclaimer" in text or "anticipate" in text):
        return True
        
    # 3. Independent Auditor's Reports (pure accounting legalese)
    if "independent auditor's report" in text or "report of independent registered public accounting firm" in text:
        return True
        
    # 4. Pure Table of Contents or Indexes
    # (Chunks with a very high density of numbers separated by dots/spaces)
    if "table of contents" in text and len(re.findall(r"\.{3,}|\s\d+\s*\n", text)) > 5:
        return True
        
    return False


def chunk_master_transcript(master_transcript, chunk_size=4000, chunk_overlap=400):
    """
    Splits the master transcript into overlapping chunks for LLM processing.

    CRITICAL DESIGN: Each individual chunk is tagged with its source filename AND a
    source authority classification. This tag is prepended to EVERY chunk (not just the
    first chunk per file), so the LLM never loses track of which document a fact came
    from even when processing chunks in isolation during batch extraction.

    This prevents two known failure modes:
    1. Cross-source contamination: LLM uses a 1978 book figure as a 2023 revenue number.
    2. Year confusion: LLM uses a historical year's column from the spreadsheet as current.

    Args:
        master_transcript: Either a string (raw text) or a dict {filename: text}
        chunk_size: Characters per chunk (default 2000, tuned for dense annual reports)
        chunk_overlap: Overlap between consecutive chunks (default 300)

    Returns:
        List of text chunk strings, each prefixed with [SOURCE FILE] and [AUTHORITY] tags.
    """
    if not master_transcript:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len,
    )

    if isinstance(master_transcript, str):
        # Legacy path: plain string with no source info available
        chunks = splitter.split_text(master_transcript)
        print(f"[Chunker] Created {len(chunks)} chunks from plain string")
        return chunks

    elif isinstance(master_transcript, dict):
        all_chunks = []
        for filename, text in master_transcript.items():
            if not text or not str(text).strip():
                continue
            authority = _classify_source(filename)
            # Split this file's text into chunks INDEPENDENTLY (no cross-file splicing)
            file_chunks = splitter.split_text(str(text))
            
            tagged_chunks = []
            dropped = 0
            for chunk in file_chunks:
                if _is_boilerplate(chunk) and "AUTHORITATIVE_DATA" not in authority:
                    dropped += 1
                    continue
                # Prepend [SOURCE FILE] + [AUTHORITY] to EVERY individual chunk
                # so the tag is never split away from its data during batch processing
                tagged_chunks.append(
                    f"[SOURCE FILE: {filename}]\n[AUTHORITY: {authority}]\n\n{chunk}"
                )
                
            all_chunks.extend(tagged_chunks)
            print(f"[Chunker] {filename}: {len(tagged_chunks)} chunks kept | {dropped} boilerplate dropped | {authority[:50]}...")
        print(
            f"[Chunker] Total: {len(all_chunks)} tagged chunks "
            f"from {len(master_transcript)} source files"
        )
        return all_chunks

    else:
        chunks = splitter.split_text(str(master_transcript))
        print(f"[Chunker] Unknown input type, converted to string: {len(chunks)} chunks")
        return chunks