import re
import pandas as pd
from datetime import datetime

MAX_ROWS = 500

MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun",
               "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_LABELS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def _detect_year_cols(df: pd.DataFrame) -> dict:
    """Return {col_name: year_int} for every column whose header contains a 4-digit year."""
    current_year = datetime.now().year
    year_cols = {}
    for col in df.columns:
        col_str = str(col).strip()
        m = re.search(r"(19|20)\d{2}", col_str)
        if m:
            y = int(m.group())
            if y <= current_year + 1:
                year_cols[col] = y
    return year_cols


_PARTIAL_YEAR_PATTERNS = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ytd|cumul|partial|month)",
    re.IGNORECASE,
)

_SINGLE_MONTH_RE = re.compile(
    r"^\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s.\-_/]*(19|20)\d{2}\s*(\(\d+\))?\s*$",
    re.IGNORECASE,
)


def _is_partial_year_col(col_name: str) -> bool:
    """True if the column header signals partial / cumulative year data."""
    return bool(_PARTIAL_YEAR_PATTERNS.search(str(col_name)))


def _is_single_month_col(col_name: str) -> bool:
    """True for a single-month column like 'Jan.2026' or 'May 2025'.
    These are excluded from per-year sections: exposing 40+ monthly columns
    tempts the LLM to sum months into fabricated totals (ARITHMETIC BAN)."""
    return bool(_SINGLE_MONTH_RE.match(str(col_name)))


def _normalise_header(val, idx: int) -> str:
    """Convert a promoted header cell to a clean string column name."""
    if pd.isna(val):
        return f"Unnamed: {idx}"
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()


def _promote_header_row(df: pd.DataFrame, max_scan: int = 10) -> pd.DataFrame:
    """
    Corporate Excel sheets often place title/blank rows ABOVE the real header row,
    so pandas reads every column as 'Unnamed: N' and year detection fails silently
    (the sheet then gets dumped as a flat mega-table → LLM year confusion).

    Scan the first rows for the row containing the most year-like cells
    (e.g. 2017, Jan.2024, '2026 Cumulative Total') and promote it to the header.
    Duplicate header names are deduplicated with a ' (n)' suffix.
    """
    if len(_detect_year_cols(df)) >= 3:
        return df  # header already usable

    for i in range(min(max_scan, len(df))):
        row = df.iloc[i]
        hits = sum(1 for v in row if re.search(r"(19|20)\d{2}", str(v)))
        if hits >= 3:
            new_cols = [_normalise_header(v, j) for j, v in enumerate(row)]
            seen: dict = {}
            deduped = []
            for c in new_cols:
                if c in seen:
                    seen[c] += 1
                    deduped.append(f"{c} ({seen[c]})")
                else:
                    seen[c] = 1
                    deduped.append(c)
            promoted = df.iloc[i + 1:].copy()
            promoted.columns = deduped
            return promoted.reset_index(drop=True)
    return df


def _fmt_value(value) -> str:
    """Render numbers exactly: integer-valued floats lose the trailing '.0'."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _build_row_labels(df: pd.DataFrame, non_year_cols: list, year_cols: dict) -> list:
    """
    Compute a descriptive label for every row.
    - Rows with a label but NO data in any year column are section headers
      (e.g. 'HEV'); they become the category prefix for following rows.
    - Rows with data but NO label are year-on-year %-change rows (per the
      workbook's Note sheet); they are labelled explicitly so the LLM never
      cites a percentage as a unit count.
    Returns a list aligned to df rows; None means 'skip this row'.
    """
    labels = []
    category = ""
    prev_label = ""
    for _, row in df.iterrows():
        parts = [
            re.sub(r"\s+", " ", str(row[c])).strip() for c in non_year_cols
            if pd.notna(row.get(c)) and str(row[c]).strip()
        ]
        label = " | ".join(p for p in parts if p)[:250]
        has_data = any(pd.notna(row.get(c)) for c in year_cols)
        if label and not has_data:
            category = label
            labels.append(None)
            continue
        if not has_data:
            labels.append(None)
            continue
        if label:
            full = f"{category} | {label}" if category else label
            prev_label = full
            labels.append(full)
        else:
            # Keep the full parent label (e.g. "Vietnam") so the LLM knows WHICH entity
            # this YoY % belongs to. Without this, "34.97%" from Vietnam's YoY row
            # gets misread as Toyota's global sales growth.
            base = prev_label or "Previous metric"
            labels.append(
                f"{base} | YoY % change vs prior year "
                f"(WARNING: values are PERCENTAGES belonging to '{base}', NOT company-wide totals or unit counts)"
            )
    return labels


def _get_month_range(df: pd.DataFrame, target_year: int) -> str:
    """
    Scan all column headers of df for individual month names associated with target_year.
    Returns a string like 'Jan-May 2026' or '' if no month columns are found.
    This is used to build the exact period label for cumulative columns, preventing
    the 'March 2026 YTD' mislabeling error.
    """
    found_months = []
    for col in df.columns:
        col_str = str(col).lower()
        if str(target_year) not in str(col):
            continue
        for idx, m in enumerate(MONTH_ORDER):
            if m in col_str:
                found_months.append(idx)
    if not found_months:
        return ""
    first = MONTH_LABELS[min(found_months)][:3]
    last = MONTH_LABELS[max(found_months)][:3]
    if first == last:
        return f"{first} {target_year}"
    return f"{first}-{last} {target_year}"


def _period_tag(col_name: str, year: int, month_range: str) -> str:
    """
    Build the period qualifier that gets embedded inside every data cell.
    For partial-year columns this uses the exact month range detected from the sheet
    (e.g. '[Jan-May 2026 - PARTIAL YEAR / CUMULATIVE. Cite as Jan-May 2026.]').
    For full-year columns this returns '[Full Year YYYY]'.
    """
    if _is_partial_year_col(str(col_name)):
        if month_range:
            return (
                f"[{month_range} - PARTIAL YEAR / CUMULATIVE. "
                f"Cite as '{month_range}'. NOT a full-year figure. "
                f"NEVER annualise or extrapolate this figure.]"
            )
        return (
            f"[{year} YTD / Cumulative - PARTIAL YEAR. "
            f"Cite with a date range. NOT a full-year figure.]"
        )
    return f"[Full Year {year} - safe to cite as annual total]"


def _build_year_sections(df: pd.DataFrame, sheet_name: str) -> str:
    """
    Output each year column as its own clearly labelled section with the period qualifier
    embedded inside every single data cell. This solves two known LLM failure modes:

    1. Year confusion: LLM picks values from the wrong year column (e.g. 2017 instead of 2026).
    2. Period mislabeling: LLM labels a Jan-May cumulative total as 'March 2026 YTD' because
       it anchors on the last individual month column it saw.

    The fix: instead of one flat table with all years side by side, each year gets its own
    section header (HISTORICAL DATA vs MOST RECENT DATA) and every cell value is suffixed
    with the exact period tag, making it impossible to confuse years or periods.
    """
    df = _promote_header_row(df)
    year_cols = _detect_year_cols(df)

    # Label columns = only the columns LEFT of the first year column.
    # Interleaved unnamed data columns (e.g. YoY % helper columns) to the right
    # would otherwise pollute row labels with raw numbers.
    cols = list(df.columns)
    year_positions = [i for i, c in enumerate(cols) if c in year_cols]
    if year_positions:
        non_year_cols = [c for i, c in enumerate(cols) if i < min(year_positions)]
    else:
        non_year_cols = [c for c in cols if c not in year_cols]

    if not year_cols:
        return f"### Sheet: {sheet_name}\n\n{df.head(MAX_ROWS).to_markdown(index=False)}"

    # Exclude single-month columns (Jan.2026, Feb.2026, ...) from the sections:
    # only full-year totals and cumulative/YTD totals are exposed to the LLM.
    section_year_cols = {
        c: y for c, y in year_cols.items() if not _is_single_month_col(c)
    }
    if not section_year_cols:
        section_year_cols = year_cols

    sorted_year_cols = sorted(section_year_cols.items(), key=lambda x: x[1])  # oldest first
    latest_col, latest_year = sorted_year_cols[-1]
    is_partial = _is_partial_year_col(str(latest_col))

    # Derive the exact month range for the cumulative column BEFORE building sections
    latest_month_range = _get_month_range(df, latest_year) if is_partial else ""

    # Build the sheet-level header
    parts = []
    header = f"### Sheet: {sheet_name}"
    header += f"\n> MOST RECENT DATA COLUMN: **{latest_col}** ({latest_year})"
    if is_partial:
        period_display = latest_month_range if latest_month_range else f"{latest_year} YTD"
        header += (
            f"\n> PARTIAL YEAR WARNING: The most recent column is CUMULATIVE / YEAR-TO-DATE data"
            f" covering **{period_display}** only. It is NOT a full-year total."
            f" Always cite figures from this column as '{period_display}'."
            f" NEVER extrapolate or annualise these figures."
        )
    if any(_is_single_month_col(c) for c in year_cols):
        header += (
            "\n> NOTE: Individual monthly columns exist in the source but are omitted here."
            " Only full-year totals and the official cumulative total are shown."
            " NEVER sum monthly or quarterly figures to create a new total."
        )
    header += (
        f"\n> SCOPE RULE: Every figure below belongs to the scope '{sheet_name}'."
        f" NEVER attribute a figure from this sheet to a different scope (e.g. a segment"
        f" figure such as electrified vehicles, Lexus, or a single country must NEVER be"
        f" presented as a company-wide or worldwide total)."
    )
    parts.append(header)

    row_labels = _build_row_labels(df, non_year_cols, year_cols)

    # Build one section per year column
    for col, year in sorted_year_cols:
        is_col_partial = _is_partial_year_col(str(col))
        is_most_recent = (col == latest_col)

        col_month_range = _get_month_range(df, year) if is_col_partial else ""
        tag = _period_tag(col, year, col_month_range)

        if is_most_recent:
            period_short = col_month_range if col_month_range else f"{year} YTD"
            section_title = f"\n#### MOST RECENT DATA - [{sheet_name}] - {col} ({period_short})"
        else:
            section_title = f"\n#### HISTORICAL DATA - [{sheet_name}] - Year {year} - {col}"

        if is_col_partial:
            period_note = col_month_range if col_month_range else "YTD"
            section_title += f" (PARTIAL YEAR: {period_note} only - NOT a full annual figure)"
        else:
            section_title += " (FULL YEAR)"

        # Embed the period tag into EVERY row value so the LLM cannot miss it
        rows = []
        for (_, row), label in zip(df.iterrows(), row_labels):
            if label is None:
                continue
            value = row.get(col)
            if pd.isna(value):
                continue
            rows.append(f"| {label} | {_fmt_value(value)} {tag} |")

        if rows:
            table = (
                f"| Metric (scope: {sheet_name}) | Value (with exact period label) |\n|---|---|\n"
                + "\n".join(rows)
            )
            parts.append(f"{section_title}\n\n{table}")

    return "\n\n".join(parts)


def parse_spreadsheet(uploaded_file) -> str:
    """Convert Excel/CSV to per-year labelled sections with period qualifiers embedded
    into every data cell, preventing LLM year-confusion and period-mislabeling errors."""
    filename = uploaded_file.name.lower()

    try:
        parts = []

        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file, nrows=MAX_ROWS)
            parts.append(_build_year_sections(df, uploaded_file.name))

        elif filename.endswith((".xls", ".xlsx")):
            sheets = pd.read_excel(uploaded_file, sheet_name=None)
            for sheet_name, df in sheets.items():
                df = df.head(MAX_ROWS)
                parts.append(_build_year_sections(df, sheet_name))
        else:
            return f"Unsupported file format: {uploaded_file.name}"

        return "\n\n".join(parts)

    except Exception as e:
        raise Exception(
            f"Failed to parse spreadsheet {uploaded_file.name}. Error: {str(e)}"
        ) from e
