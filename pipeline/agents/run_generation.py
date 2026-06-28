"""Sequential orchestration for Agents 2 and 3."""

from typing import Callable, Optional

from pipeline.agents.agent_storyteller import run_agent_2
from pipeline.agents.agent_analyst import run_agent_3


def run_generation(
    filtered_fact_sheet,
    ui_config: dict,
    on_agent2_progress: Optional[Callable[[], None]] = None,
    on_agent3_progress: Optional[Callable[[], None]] = None,
) -> dict:
    """
    Run Agent 2 then Agent 3 sequentially.
    Returns {"narrative": dict, "exhibits": str, "discussion_questions": list}.
    """
    narrative = run_agent_2(filtered_fact_sheet, ui_config)
    if on_agent2_progress:
        on_agent2_progress()

    analyst = run_agent_3(filtered_fact_sheet, ui_config)
    if on_agent3_progress:
        on_agent3_progress()

    return {
        "narrative": narrative,
        "exhibits": analyst.get("exhibits", ""),
        "discussion_questions": analyst.get("discussion_questions", []),
    }
