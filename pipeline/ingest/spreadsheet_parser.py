import re
import pandas as pd
from datetime import datetime

MAX_ROWS = 500


def _detect_latest_year_col(df: pd.DataFrame) -> str | None:
    """Return the column name that represents the most recent year, or None."""
    current_year = datetime.now().year
    year_cols = {}
    for col in df.columns:
        col_str = str(col).strip()
        m = re.search(r"(19|20)\d{2}", col_str)
        if m:
            y = int(m.group())
            if y <= current_year:
                year_cols[col] = y
    if not year_cols:
        return None
    return max(year_cols, key=year_cols.get)


_PARTIAL_YEAR_PATTERNS = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ytd|cumul|partial|month)",
    re.IGNORECASE,
)


def _is_partial_year_col(col_name: str) -> bool:
    """Return True if the column header indicates partial / cumulative year data."""
    return bool(_PARTIAL_YEAR_PATTERNS.search(str(col_name)))


def parse_spreadsheet(uploaded_file) -> str:
    """Convert Excel/CSV to Markdown tables with sheet headers, row cap,
    and a prominent annotation of the most recent year column so the LLM
    always uses up-to-date figures rather than historical ones."""
    filename = uploaded_file.name.lower()

    try:
        parts = []

        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file, nrows=MAX_ROWS)
            latest_col = _detect_latest_year_col(df)
            header = f"### Sheet: {uploaded_file.name}"
            if latest_col:
                header += f"\n> ⚠️ MOST RECENT DATA COLUMN: **{latest_col}** — always prefer this column over older year columns."
            md = df.to_markdown(index=False)
            parts.append(f"{header}\n\n{md}")

        elif filename.endswith((".xls", ".xlsx")):
            sheets = pd.read_excel(uploaded_file, sheet_name=None)
            for sheet_name, df in sheets.items():
                df = df.head(MAX_ROWS)
                latest_col = _detect_latest_year_col(df)
                header = f"### Sheet: {sheet_name}"
                if latest_col:
                    if _is_partial_year_col(str(latest_col)):
                        header += (
                            f"\n> ⚠️ MOST RECENT DATA COLUMN: **{latest_col}**"
                            f" — always prefer this column over older year columns when extracting facts."
                            f"\n> ⛔ WARNING: This column represents PARTIAL YEAR / CUMULATIVE data "
                            f"(e.g. Jan–May only). Do NOT extrapolate, multiply, or annualise these "
                            f"figures to estimate a full-year total. Always cite them with a date range label "
                            f"such as \"Jan–May {latest_col}\"."
                        )
                    else:
                        header += f"\n> ⚠️ MOST RECENT DATA COLUMN: **{latest_col}** — always prefer this column over older year columns when extracting facts."
                md = df.to_markdown(index=False)
                parts.append(f"{header}\n\n{md}")
        else:
            return f"Unsupported file format: {uploaded_file.name}"

        return "\n\n".join(parts)

    except Exception as e:
        raise Exception(f"Failed to parse spreadsheet {uploaded_file.name}. Error: {str(e)}") from e

