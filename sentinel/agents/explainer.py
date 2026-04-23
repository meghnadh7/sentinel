from __future__ import annotations
"""Explainer Agent — SHAP explainability and compliance RAG Q&A."""

import json
from typing import Any

from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from sentinel.config import get_settings

settings = get_settings()


class SHAPAnalysisInput(BaseModel):
    model_id: str = Field(description="Model ID to analyze")
    n_samples: int = Field(default=500, description="Number of prediction samples to use")


class SHAPAnalysisTool(BaseTool):
    name: str = "SHAPAnalysisTool"
    description: str = (
        "Runs SHAP explainability analysis on model predictions. "
        "Returns feature importance rankings and detects behavior changes."
    )
    args_schema: type[BaseModel] = SHAPAnalysisInput

    def _run(self, model_id: str, n_samples: int = 500) -> str:
        try:
            import asyncio
            import numpy as np
            from sentinel.data.database import AsyncSessionLocal
            from sentinel.data.models import ModelPrediction
            from sqlalchemy import select

            async def _fetch():
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(ModelPrediction)
                        .where(ModelPrediction.model_id == model_id)
                        .order_by(ModelPrediction.timestamp.desc())
                        .limit(n_samples)
                    )
                    return result.scalars().all()

            predictions = asyncio.get_event_loop().run_until_complete(_fetch())
            if not predictions:
                return json.dumps({"error": "No predictions found"})

            feature_keys = list(predictions[0].input_features.keys()) if predictions else []
            if not feature_keys:
                return json.dumps({"error": "No input features found"})

            X = np.array([
                [p.input_features.get(k, 0.0) for k in feature_keys]
                for p in predictions
            ])

            # Try to load model from MLflow for SHAP
            try:
                from sentinel.registry.mlflow_client import SentinelMLflowClient
                from sentinel.data.models import Model
                client = SentinelMLflowClient()
                ml_models = client.list_registered_models()
                # Find matching model
                model_name = None
                for m in ml_models:
                    if model_id in m.get("name", "").lower() or m.get("name", ""):
                        model_name = m["name"]
                        break

                if model_name:
                    version_info = client.get_model_versions(model_name)
                    if version_info:
                        sklearn_model = client.load_model_for_sandbox(
                            model_name, version_info[0]["version"]
                        )
                        from sentinel.audit.explainability import run_shap_analysis
                        result = run_shap_analysis(sklearn_model, X, feature_keys)
                        return json.dumps({
                            "model_id": model_id,
                            "n_samples": len(predictions),
                            "feature_importance": result.feature_importance,
                            "top_features": result.top_features,
                            "spearman_rho": result.spearman_rho,
                            "stability_alert": result.stability_alert,
                        })
            except Exception:
                pass

            # Fallback: use raw prediction magnitude as proxy importance
            importance = {k: float(abs(X[:, i].std())) for i, k in enumerate(feature_keys)}
            return json.dumps({
                "model_id": model_id,
                "n_samples": len(predictions),
                "feature_importance": importance,
                "top_features": sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5],
                "note": "Proxy importance — model not loaded from registry",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


class StabilityMonitorInput(BaseModel):
    model_id: str
    current_importance: dict[str, float]
    baseline_importance: dict[str, float]


class StabilityMonitorTool(BaseTool):
    name: str = "StabilityMonitorTool"
    description: str = "Computes Spearman ρ between current and baseline SHAP rankings."
    args_schema: type[BaseModel] = StabilityMonitorInput

    def _run(self, model_id: str, current_importance: dict[str, float],
             baseline_importance: dict[str, float]) -> str:
        try:
            from sentinel.audit.explainability import compute_spearman_stability
            rho = compute_spearman_stability(current_importance, baseline_importance)
            alert = rho < settings.shap_stability_threshold
            return json.dumps({
                "model_id": model_id,
                "spearman_rho": rho,
                "threshold": settings.shap_stability_threshold,
                "stability_alert": alert,
                "message": f"Model behavior change detected (ρ={rho:.3f})" if alert else "Stable",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


class LlamaIndexRAGInput(BaseModel):
    question: str = Field(description="Compliance question to ask")
    regulation: str = Field(default="", description="Specific regulation: SR-11-7, FCRA, EU-AI-ACT, NIST")


class LlamaIndexRAGTool(BaseTool):
    name: str = "LlamaIndexRAGTool"
    description: str = (
        "Queries the LlamaIndex compliance document RAG index to answer regulatory questions. "
        "Covers SR 11-7, FCRA, Regulation B, EU AI Act, and NIST AI RMF."
    )
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


class MLflowLogInput(BaseModel):
    model_id: str
    run_id: str
    feature_importance: dict[str, float]
    spearman_rho: float | None = None


class MLflowLogTool(BaseTool):
    name: str = "MLflowLogTool"
    description: str = "Logs SHAP artifacts and stability scores to MLflow."
    args_schema: type[BaseModel] = MLflowLogInput

    def _run(self, model_id: str, run_id: str, feature_importance: dict[str, float],
             spearman_rho: float | None = None) -> str:
        try:
            from sentinel.registry.mlflow_client import SentinelMLflowClient
            client = SentinelMLflowClient()
            client.log_shap_artifact(run_id, feature_importance)
            if spearman_rho is not None:
                import mlflow
                with mlflow.start_run(run_id=run_id):
                    mlflow.log_metric("shap_spearman_rho", spearman_rho)
            return json.dumps({"status": "logged", "model_id": model_id, "run_id": run_id})
        except Exception as e:
            return json.dumps({"error": str(e)})


def create_explainer_agent() -> Agent:
    return Agent(
        role="ML Explainability and Transparency Analyst",
        goal=(
            "Run SHAP-based explainability monitoring on all tabular models. Detect model behavior "
            "changes via Spearman rank correlation. Answer compliance questions using the LlamaIndex "
            "RAG index over SR 11-7, FCRA, EU AI Act, and NIST AI RMF with grounded citations."
        ),
        backstory=(
            "You are an AI transparency expert combining deep ML explainability knowledge with "
            "regulatory compliance expertise. You use SHAP values to explain model decisions and "
            "monitor for behavioral drift. You ground all compliance answers in specific regulatory "
            "text retrieved from the RAG index — no hallucination. You understand that explainability "
            "is a legal requirement under FCRA and Regulation B for consumer-facing financial models."
        ),
        tools=[
            SHAPAnalysisTool(),
            StabilityMonitorTool(),
            LlamaIndexRAGTool(),
            MLflowLogTool(),
        ],
        max_iter=settings.agent_max_tool_calls,
        verbose=True,
    )


def create_explainability_task(agent: Agent, model_id: str) -> Task:
    return Task(
        description=(
            f"Run explainability analysis for model {model_id}. "
            "Steps: (1) Run SHAPAnalysisTool to compute feature importance. "
            "(2) Query LlamaIndexRAGTool: 'What does SR 11-7 require for explainability of consumer-facing models?' "
            "(3) If run_id is available, log SHAP artifacts to MLflow. "
            "(4) Return the top 5 features by importance and the RAG-grounded compliance citation."
        ),
        expected_output=(
            "JSON with: model_id, top_features (list), spearman_rho, stability_alert, "
            "compliance_citation (SR 11-7 text), fcra_requirement."
        ),
        agent=agent,
    )
