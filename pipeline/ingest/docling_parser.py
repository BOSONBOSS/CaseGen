import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend


def parse_pdf(uploaded_file, max_pages: int = None) -> str:
    """
    Uses IBM Docling to extract text from PDFs.
    max_pages: cap processing for dev/testing. None = entire document.
    """
    os.makedirs("uploads", exist_ok=True)

    temp_path = os.path.join("uploads", uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
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

        convert_kwargs = {"source": temp_path}
        if max_pages is not None:
            convert_kwargs["page_range"] = (1, max_pages)

        result = converter.convert(**convert_kwargs)
        markdown_text = result.document.export_to_markdown()

        # Prefix with page markers if docling exposes page count
        try:
            num_pages = len(result.document.pages) if hasattr(result.document, "pages") else 0
            if num_pages > 1:
                lines = markdown_text.split("\n\n")
                chunk_size = max(1, len(lines) // num_pages)
                marked = []
                page = 1
                for i, block in enumerate(lines):
                    if i > 0 and i % chunk_size == 0 and page < num_pages:
                        page += 1
                    marked.append(f"<!-- page {page} -->\n{block}")
                markdown_text = "\n\n".join(marked)
        except Exception:
            pass

        os.remove(temp_path)
        print(f"[PDF Parser] Extracted {len(markdown_text):,} chars from {uploaded_file.name}")
        return markdown_text

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
