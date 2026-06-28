import pandas as pd

MAX_ROWS = 500


def parse_spreadsheet(uploaded_file) -> str:
    """Convert Excel/CSV to Markdown tables with sheet headers and row cap."""
    filename = uploaded_file.name.lower()

    try:
        parts = []

        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file, nrows=MAX_ROWS)
            md = df.to_markdown(index=False)
            parts.append(f"### Sheet: {uploaded_file.name}\n\n{md}")

        elif filename.endswith((".xls", ".xlsx")):
            sheets = pd.read_excel(uploaded_file, sheet_name=None)
            for sheet_name, df in sheets.items():
                df = df.head(MAX_ROWS)
                md = df.to_markdown(index=False)
                parts.append(f"### Sheet: {sheet_name}\n\n{md}")
        else:
            return f"Unsupported file format: {uploaded_file.name}"

        return "\n\n".join(parts)

    except Exception as e:
        raise Exception(f"Failed to parse spreadsheet {uploaded_file.name}. Error: {str(e)}") from e
