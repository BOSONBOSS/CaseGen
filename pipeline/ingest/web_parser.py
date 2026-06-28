import os
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

def _extract_main_text(soup: BeautifulSoup) -> str:
    """Prefer semantic main content regions before falling back to body."""
    for selector in [
        {"name": "main"},
        {"name": "article"},
        {"attrs": {"role": "main"}},
        {"name": "div", "attrs": {"id": "content"}},
        {"name": "div", "attrs": {"class": "content"}},
    ]:
        el = soup.find(**selector)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 300:
                return text

    body = soup.find("body")
    if body:
        return body.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def _detect_homepage_junk(text: str) -> Optional[str]:
    if not text or len(text) < 200:
        return None
    lower = text.lower()
    nav_keywords = ["cookie", "privacy policy", "sign in", "subscribe", "accept all"]
    nav_hits = sum(1 for kw in nav_keywords if kw in lower)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    short_ratio = sum(1 for ln in lines if len(ln) < 40) / max(len(lines), 1)
    if nav_hits >= 2 and short_ratio > 0.45:
        return (
            "Content looks like a website homepage (nav menus, cookie banners). "
            "Link directly to a PDF or article URL instead."
        )
    return None


def parse_url(url: str) -> Tuple[str, Optional[str]]:
    """
    Fetch URL and extract clean text.
    Returns (text, warning_or_none).
    Direct PDF URLs are parsed via Docling.
    """
    url = url.strip()
    if not url:
        return "", None

    if url.lower().endswith(".pdf") or ".pdf?" in url.lower():
        return _parse_pdf_url(url)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CaseGen/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type:
            return _parse_pdf_bytes(response.content, url)

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = _extract_main_text(soup)
        warning = _detect_homepage_junk(text)
        return text, warning

    except Exception as e:
        raise Exception(f"Failed to extract text from {url}. Error: {str(e)}") from e


def _parse_pdf_url(url: str) -> Tuple[str, Optional[str]]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return _parse_pdf_bytes(response.content, url)


def _parse_pdf_bytes(content: bytes, source_label: str) -> Tuple[str, Optional[str]]:
    os.makedirs("uploads", exist_ok=True)
    safe_name = source_label.split("/")[-1][:80] or "web_pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    temp_path = os.path.join("uploads", safe_name)

    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )
        result = converter.convert(source=temp_path)
        text = result.document.export_to_markdown()
        return text, None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
