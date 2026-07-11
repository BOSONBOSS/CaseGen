# from langchain_text_splitters import RecursiveCharacterTextSplitter

# def chunk_master_transcript(master_transcript, chunk_size=1000, chunk_overlap=200):
#     if not master_transcript:
#         return []

#     combined_text = ""

#     if isinstance(master_transcript, str):
#         combined_text = master_transcript

#     elif isinstance(master_transcript, dict):
#         for filename, text in master_transcript.items():
#             if text and text.strip():
#                 combined_text += f"\n\n[Source: {filename}]\n{text}"

#     else:
#         combined_text = str(master_transcript)

#     if not combined_text.strip():
#         return []

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap,
#         separators=["\n\n", "\n", ".", " ", ""],
#         length_function=len,
#     )

#     chunks = splitter.split_text(combined_text)
#     print(f"[Chunker] Created {len(chunks)} chunks from {len(combined_text)} characters")
#     return chunks

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_master_transcript(master_transcript, chunk_size=2000, chunk_overlap=300):
    """
    Splits the master transcript into overlapping chunks for LLM processing.

    chunk_size=2000 / chunk_overlap=300 is tuned for dense corporate documents
    such as annual reports and integrated reports. Smaller documents (press releases,
    articles) will produce fewer, larger chunks — which is fine.

    Args:
        master_transcript: Either a string (raw text) or a dict {filename: text}
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between consecutive chunks

    Returns:
        List of text chunk strings
    """
    if not master_transcript:
        return []

    combined_text = ""

    if isinstance(master_transcript, str):
        combined_text = master_transcript
        print(f"[Chunker] Received string of length: {len(combined_text)}")

    elif isinstance(master_transcript, dict):
        for filename, text in master_transcript.items():
            if text and text.strip():
                combined_text += f"\n\n[Source: {filename}]\n{text}"
        print(f"[Chunker] Combined {len(master_transcript)} files")

    else:
        combined_text = str(master_transcript)
        print(f"[Chunker] Received unknown type, converted to string")

    if not combined_text.strip():
        print("[Chunker] Warning: No text content found")
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_text(combined_text)
    print(f"[Chunker] Created {len(chunks)} chunks from {len(combined_text)} characters")
    return chunks