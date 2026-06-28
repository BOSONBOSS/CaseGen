"""Parallel orchestration for Agents 2 and 3."""

from concurrent.futures import ThreadPoolExecutor, as_completed
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
    Run Agent 2 and Agent 3 in parallel.
    Returns {"narrative": dict, "exhibits": str, "discussion_questions": list}.
    """
    results = {"narrative": {}, "exhibits": "", "discussion_questions": []}

    def _agent2():
        narrative = run_agent_2(filtered_fact_sheet, ui_config)
        if on_agent2_progress:
            on_agent2_progress()
        return ("narrative", narrative)

    def _agent3():
        analyst = run_agent_3(filtered_fact_sheet, ui_config)
        if on_agent3_progress:
            on_agent3_progress()
        return ("analyst", analyst)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_agent2), executor.submit(_agent3)]
        for future in as_completed(futures):
            key, value = future.result()
            if key == "narrative":
                results["narrative"] = value
            else:
                results["exhibits"] = value.get("exhibits", "")
                results["discussion_questions"] = value.get("discussion_questions", [])

    return results
