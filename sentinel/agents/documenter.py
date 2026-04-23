from __future__ import annotations
"""Documenter Agent — auto-generates SR 11-7 compliant model cards."""

import json
from typing import Any

from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from sentinel.config import get_settings

settings = get_settings()


class LlamaIndexRAGInput(BaseModel):
    question: str = Field(description="Regulatory evidence to retrieve")
    regulation: str = Field(default="", description="Filter by regulation")


class LlamaIndexRAGTool(BaseTool):
    name: str = "LlamaIndexRAGTool"
    description: str = "Retrieves regulatory evidence for model card sections from the compliance index."
    args_schema: type[BaseModel] = LlamaIndexRAGInput

    def _run(self, question: str, regulation: str = "") -> str:
        try:
            from sentinel.rag.query_engine import query_with_citations
            result = query_with_citations(question, regulation or None)
            return json.dumps({
                "question": question,
                "answer": result.answer,
                "confidence": result.confidence,
                "sources": result.sources[:3],
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


class ModelCardGeneratorInput(BaseModel):
    model_id: str
    fairness_summary: dict[str, Any]
    red_team_summary: dict[str, Any]
    explainability_summary: dict[str, Any]
    regulatory_evidence: dict[str, str]


class ModelCardGeneratorTool(BaseTool):
    name: str = "ModelCardGeneratorTool"
    description: str = "Assembles a structured model card (JSON-LD + Markdown) from agent outputs."
    args_schema: type[BaseModel] = ModelCardGeneratorInput

    def _run(
        self,
        model_id: str,
        fairness_summary: dict[str, Any],
        red_team_summary: dict[str, Any],
        explainability_summary: dict[str, Any],
        regulatory_evidence: dict[str, str],
    ) -> str:
        try:
            from sentinel.compliance.model_card import generate_model_card
            import asyncio

            async def _generate():
                return await generate_model_card(
                    model_id=model_id,
                    fairness_summary=fairness_summary,
                    red_team_summary=red_team_summary,
                    explainability_summary=explainability_summary,
                    regulatory_evidence=regulatory_evidence,
                )

            card = asyncio.get_event_loop().run_until_complete(_generate())
            return json.dumps({
                "model_card_id": card["id"],
                "completeness_score": card["completeness_score"],
                "sections": list(card["content_json"].keys()),
                "markdown_preview": card["content_markdown"][:500] if card.get("content_markdown") else "",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


class MySQLWriteInput(BaseModel):
    model_id: str
    card_data: dict[str, Any]
    completeness_score: float


class MySQLWriteTool(BaseTool):
    name: str = "MySQLWriteTool"
    description: str = "Stores model card versions in MySQL."
    args_schema: type[BaseModel] = MySQLWriteInput

    def _run(self, model_id: str, card_data: dict[str, Any], completeness_score: float) -> str:
        try:
            import asyncio, uuid
            from sentinel.data.database import AsyncSessionLocal
            from sentinel.data.models import ModelCard
            from sentinel.compliance.model_card import render_markdown

            async def _write():
                async with AsyncSessionLocal() as session:
                    from sentinel.data.repositories.model_cards import ModelCardRepository
                    repo = ModelCardRepository(session)
                    version = await repo.get_next_version(model_id)
                    card = ModelCard(
                        id=str(uuid.uuid4()),
                        model_id=model_id,
                        version=version,
                        content_json=card_data,
                        content_markdown=render_markdown(card_data),
                        completeness_score=completeness_score,
                    )
                    await repo.save(card)
                    await session.commit()
                    return card.id

            card_id = asyncio.get_event_loop().run_until_complete(_write())
            return json.dumps({"status": "saved", "card_id": card_id, "version": "latest"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class CompletenessScoreInput(BaseModel):
    card_data: dict[str, Any]


class CompletenessScoreTool(BaseTool):
    name: str = "CompletenessScoreTool"
    description: str = "Scores documentation completeness against SR 11-7 requirements."
    args_schema: type[BaseModel] = CompletenessScoreInput

    def _run(self, card_data: dict[str, Any]) -> str:
        required_sections = [
            "model_purpose", "risk_tier", "training_data_provenance",
            "fairness_metrics_summary", "red_team_results_summary",
            "explainability_summary", "approval_chain", "nist_ai_rmf_mapping",
            "regulatory_citations", "known_limitations",
        ]
        present = sum(
            1 for s in required_sections
            if s in card_data and card_data[s] not in (None, "", {}, [])
        )
        score = present / len(required_sections)
        missing = [s for s in required_sections if s not in card_data or not card_data[s]]
        return json.dumps({
            "completeness_score": score,
            "sections_present": present,
            "sections_required": len(required_sections),
            "missing_sections": missing,
            "passes_threshold": score >= settings.doc_completeness_threshold,
        })


def create_documenter_agent() -> Agent:
    return Agent(
        role="Regulatory Compliance Documentation Specialist",
        goal=(
            "Auto-generate complete, grounded model cards for all registered models. "
            "Use LlamaIndex to retrieve regulatory evidence as citations (not hallucination). "
            "Produce JSON-LD and Markdown outputs. Target completeness score >90%."
        ),
        backstory=(
            "You are a compliance documentation expert who has spent years ensuring financial "
            "institutions meet SR 11-7 model risk management requirements. You know that poor "
            "documentation is one of the top findings in Fed examinations. You ground every "
            "claim in specific regulatory text retrieved from the RAG index. You produce "
            "documentation that would satisfy a Federal Reserve examiner."
        ),
        tools=[
            LlamaIndexRAGTool(),
            ModelCardGeneratorTool(),
            MySQLWriteTool(),
            CompletenessScoreTool(),
        ],
        max_iter=settings.agent_max_tool_calls,
        verbose=True,
    )


def create_documentation_task(
    agent: Agent,
    model_id: str,
    fairness_summary: dict | None = None,
    red_team_summary: dict | None = None,
    explainability_summary: dict | None = None,
) -> Task:
    return Task(
        description=(
            f"Generate a complete SR 11-7 compliant model card for model {model_id}. "
            "Steps: (1) Query LlamaIndexRAGTool for SR 11-7 documentation requirements. "
            "(2) Query LlamaIndexRAGTool for NIST AI RMF mapping guidance. "
            "(3) Assemble the model card using ModelCardGeneratorTool with all available summaries. "
            "(4) Score completeness using CompletenessScoreTool. "
            "(5) Save to MySQL using MySQLWriteTool. "
            f"Use these inputs if available — fairness: {fairness_summary}, "
            f"red_team: {red_team_summary}, explainability: {explainability_summary}."
        ),
        expected_output=(
            "JSON with: model_card_id, completeness_score, all_sections_present (bool), "
            "missing_sections (list), regulatory_citations (dict), passes_threshold (bool)."
        ),
        agent=agent,
    )
