"""Sequential orchestration for Agents 2 and 3."""

import re
from typing import Callable, Optional

from pipeline.agents.agent_storyteller import run_agent_2
from pipeline.agents.agent_analyst import run_agent_3


def _build_exhibit_index(exhibits_markdown: str) -> dict:
    """
    Parse the exhibits markdown to extract a numbered index.
    E.g. '**Exhibit 1: Key Company Facts**' -> {'key company facts': 1, ...}
    Returns a dict of lowercase-title -> exhibit_number for the storyteller to reference.
    """
    index = {}
    # Match patterns like: **Exhibit 1: Some Title** or **Exhibit 1 — Some Title**
    for m in re.finditer(r"\*\*Exhibit\s+(\d+)[:\—\-–]\s*(.+?)\*\*", exhibits_markdown):
        num = int(m.group(1))
        title = m.group(2).strip().lower()
        index[title] = num
    return index


def run_generation(
    filtered_fact_sheet,
    ui_config: dict,
    on_agent2_progress: Optional[Callable[[], None]] = None,
    on_agent3_progress: Optional[Callable[[], None]] = None,
) -> dict:
    """
    Run Agent 3 first (to build exhibit index), then Agent 2 (narrative with inline refs).
    Returns {"narrative": dict, "exhibits": str, "discussion_questions": list}.
    """
    # Agent 3 runs FIRST so we have numbered exhibits before prose is written
    analyst = run_agent_3(filtered_fact_sheet, ui_config)
    if on_agent3_progress:
        on_agent3_progress()

    exhibits_md = analyst.get("exhibits", "") or ""
    exhibit_index = _build_exhibit_index(exhibits_md)

    # Agent 2 receives exhibit index so it can write "(see Exhibit N)" inline
    narrative = run_agent_2(filtered_fact_sheet, ui_config, exhibit_index=exhibit_index)
    if on_agent2_progress:
        on_agent2_progress()

    return {
        "narrative": narrative,
        "exhibits": exhibits_md,
        "exhibit_index": exhibit_index,
        "discussion_questions": analyst.get("discussion_questions", []),
    }
