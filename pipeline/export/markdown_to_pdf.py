"""Convert Markdown to PDF via HTML and WeasyPrint."""

import io
import re


def _markdown_to_html(markdown: str) -> str:
    html_parts = []
    lines = markdown.splitlines()
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        html_parts.append("<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%;margin:12px 0;'>")
        for ri, row in enumerate(table_rows):
            tag = "th" if ri == 0 else "td"
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(f"<{tag}>{cell}</{tag}>")
            html_parts.append("</tr>")
        html_parts.append("</table>")
        table_rows = []
        in_table = False

    for line in lines:
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue
        elif in_table:
            flush_table()

        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_parts.append(f"<h3>{line[4:]}</h3>")
        elif line.strip():
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            html_parts.append(f"<p>{text}</p>")

    if in_table:
        flush_table()

    body = "\n".join(html_parts)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@page {{ margin: 1in; }}
body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; line-height: 1.5; color: #000; }}
h1 {{ font-size: 18pt; }} h2 {{ font-size: 14pt; margin-top: 18px; }} h3 {{ font-size: 12pt; }}
table {{ font-size: 11pt; }}
</style></head><body>{body}</body></html>"""


def markdown_to_pdf(markdown: str) -> bytes:
    """Convert Markdown to PDF bytes."""
    from weasyprint import HTML

    html = _markdown_to_html(markdown)
    pdf_buffer = io.BytesIO()
    HTML(string=html).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer.read()
