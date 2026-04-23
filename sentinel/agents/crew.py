from __future__ import annotations
"""CrewAI Crew — wires all four Sentinel agents."""

import json
from typing import Any

from crewai import Crew, Process

from sentinel.agents.auditor import create_auditor_agent, create_fairness_audit_task
from sentinel.agents.documenter import create_documenter_agent, create_documentation_task
from sentinel.agents.explainer import create_explainer_agent, create_explainability_task
from sentinel.agents.red_team import create_red_team_agent, create_red_team_task
from sentinel.config import get_settings

settings = get_settings()


def build_audit_crew(model_id: str) -> Crew:
    """Build the full four-agent audit crew for a given model."""
    auditor = create_auditor_agent()
    red_teamer = create_red_team_agent()
    explainer = create_explainer_agent()
    documenter = create_documenter_agent()

    fairness_task = create_fairness_audit_task(auditor, model_id)
    red_team_task = create_red_team_task(red_teamer, model_id)
    explainability_task = create_explainability_task(explainer, model_id)
    documentation_task = create_documentation_task(
        documenter,
        model_id,
        fairness_summary={"note": "populated from fairness_task output"},
        red_team_summary={"note": "populated from red_team_task output"},
        explainability_summary={"note": "populated from explainability_task output"},
    )

    return Crew(
        agents=[auditor, red_teamer, explainer, documenter],
        tasks=[fairness_task, red_team_task, explainability_task, documentation_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=10,
    )


def run_full_audit(model_id: str) -> dict[str, Any]:
    """Run the complete audit pipeline for a model."""
    from sentinel.data.audit_log import append_audit_entry
    from sentinel.data.database import AsyncSessionLocal
    import asyncio

    async def _log_start():
        async with AsyncSessionLocal() as session:
            await append_audit_entry(
                session,
                agent_name="crew",
                action="audit_started",
                model_id=model_id,
                result={"trigger": "on_demand"},
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_log_start())

    if settings.use_mock_llm:
        from sentinel.mock_llm import mock_run_full_audit
        result_dict = mock_run_full_audit(model_id)
        outcome = result_dict["audit_result"]
    else:
        crew = build_audit_crew(model_id)
        outcome = str(crew.kickoff())
        result_dict = {"model_id": model_id, "audit_result": outcome}

    async def _log_complete(outcome: str):
        async with AsyncSessionLocal() as session:
            await append_audit_entry(
                session,
                agent_name="crew",
                action="audit_completed",
                model_id=model_id,
                result={"outcome": outcome[:500] if outcome else ""},
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_log_complete(outcome))

    return result_dict


if __name__ == "__main__":
    import sys
    model_id = sys.argv[1] if len(sys.argv) > 1 else "model-advisor-v2"
    print(f"Running full audit for model: {model_id}")
    result = run_full_audit(model_id)
    print(json.dumps(result, indent=2))
