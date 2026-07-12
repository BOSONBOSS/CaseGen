"""Fast PDF parser using PyMuPDF — lightweight text extraction for standard PDFs."""

import os


def parse_pdf_fast(uploaded_file, max_pages: int = None) -> str:
    """
    Uses PyMuPDF (fitz) to extract text from PDFs.
    Significantly faster than Docling but does not preserve complex table layouts.
    max_pages: cap processing for dev/testing. None = entire document.

    Import style: `import pymupdf as fitz` supports both the legacy `fitz` name
    and the new canonical `pymupdf` package name — future-proof either way.
    """
    try:
        import pymupdf as fitz  # noqa: F401 — also exposes legacy 'fitz' API
    except ImportError as e:
        raise RuntimeError(
            "Fast PDF parsing requires the 'pymupdf' package. "
            "Run: pip install 'pymupdf>=1.24.0'"
        ) from e

    os.makedirs("uploads", exist_ok=True)
    temp_path = os.path.join("uploads", uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        import pymupdf as fitz

        doc = fitz.open(temp_path)
        total_pages = len(doc)
        limit = min(max_pages, total_pages) if max_pages else total_pages

        pages_text = []
        for i in range(limit):
            page = doc[i]
            text = page.get_text("text").strip()
            if text:
                pages_text.append(f"<!-- page {i + 1} -->\n{text}")

        doc.close()
        os.remove(temp_path)

        result = "\n\n".join(pages_text)
        print(
            f"[Fast PDF Parser] Extracted {len(result):,} chars from "
            f"{uploaded_file.name} ({limit}/{total_pages} pages)"
        )
        return result

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        err = str(e).lower()
        if "password" in err or "encrypted" in err:
            raise Exception(
                f"PDF {uploaded_file.name} is password-protected. "
                "Remove the password and re-upload."
            ) from e
        if "corrupt" in err or "invalid" in err:
            raise Exception(
                f"PDF {uploaded_file.name} appears corrupted. Try re-downloading the file."
            ) from e
        raise Exception(f"Failed to parse PDF {uploaded_file.name}. Error: {str(e)}") from e
