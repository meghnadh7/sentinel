from __future__ import annotations
"""Auditor Agent — continuous fairness monitoring."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from sentinel.audit.fairness import run_fairness_audit
from sentinel.config import get_settings

settings = get_settings()
UTC = timezone.utc


class FairnessComputationInput(BaseModel):
    model_id: str = Field(description="Model ID to audit")
    lookback_days: int = Field(default=7, description="Days of predictions to include")


class FairnessComputationTool(BaseTool):
    name: str = "FairnessComputationTool"
    description: str = (
        "Computes fairness metrics (Demographic Parity Ratio, Equalized Odds Difference, "
        "Disparate Impact Ratio) across protected classes for a given model. "
        "Returns metric results and alert levels."
    )
    args_schema: type[BaseModel] = FairnessComputationInput

    def _run(self, model_id: str, lookback_days: int = 7) -> str:
        try:
            from sentinel.data.database import AsyncSessionLocal
            from sentinel.data.models import ModelPrediction
            import asyncio
            from sqlalchemy import select

            async def _fetch():
                since = datetime.now(UTC) - timedelta(days=lookback_days)
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(ModelPrediction)
                        .where(ModelPrediction.model_id == model_id)
                        .where(ModelPrediction.timestamp >= since)
                        .limit(10000)
                    )
                    return result.scalars().all()

            predictions = asyncio.get_event_loop().run_until_complete(_fetch())
            if not predictions:
                return json.dumps({"error": f"No predictions found for model {model_id}"})

            rows = []
            for p in predictions:
                rows.append({
                    "sex": p.sex,
                    "race": p.race,
                    "ethnicity": p.ethnicity,
                    "age_bucket": p.age_bucket,
                    "income_bracket": p.income_bracket,
                    "decision": p.decision,
                    "prediction": p.prediction,
                    "confidence": p.confidence,
                })
            df = pd.DataFrame(rows)
            results = run_fairness_audit(df)

            output = []
            for r in results:
                output.append({
                    "protected_class": r.protected_class,
                    "demographic_parity_ratio": r.demographic_parity_ratio,
                    "equalized_odds_diff": r.equalized_odds_diff,
                    "disparate_impact_ratio": r.disparate_impact_ratio,
                    "sample_size": r.sample_size,
                    "alert_level": r.alert_level,
                    "ci_95": [r.dp_ratio_ci_lower, r.dp_ratio_ci_upper],
                })
            return json.dumps({"model_id": model_id, "fairness_results": output})
        except Exception as e:
            return json.dumps({"error": str(e)})


class MySQLQueryInput(BaseModel):
    query_type: str = Field(description="Type: 'recent_predictions' | 'model_info'")
    model_id: str = Field(description="Model ID to query")
    limit: int = Field(default=100)


class MySQLQueryTool(BaseTool):
    name: str = "MySQLQueryTool"
    description: str = "Reads model prediction logs and model metadata from MySQL."
    args_schema: type[BaseModel] = MySQLQueryInput

    def _run(self, query_type: str, model_id: str, limit: int = 100) -> str:
        try:
            import asyncio
            from sentinel.data.database import AsyncSessionLocal
            from sentinel.data.models import Model, ModelPrediction
            from sqlalchemy import select

            async def _fetch():
                async with AsyncSessionLocal() as session:
                    if query_type == "model_info":
                        result = await session.execute(
                            select(Model).where(Model.id == model_id)
                        )
                        m = result.scalar_one_or_none()
                        if not m:
                            return {"error": "Model not found"}
                        return {
                            "id": m.id,
                            "name": m.name,
                            "version": m.version,
                            "risk_tier": m.risk_tier,
                            "validation_status": m.validation_status,
                        }
                    else:
                        result = await session.execute(
                            select(ModelPrediction)
                            .where(ModelPrediction.model_id == model_id)
                            .order_by(ModelPrediction.timestamp.desc())
                            .limit(limit)
                        )
                        preds = result.scalars().all()
                        return {"count": len(preds), "sample": [
                            {"decision": p.decision, "sex": p.sex, "race": p.race}
                            for p in preds[:5]
                        ]}

            data = asyncio.get_event_loop().run_until_complete(_fetch())
            return json.dumps(data)
        except Exception as e:
            return json.dumps({"error": str(e)})


class RedisWriteInput(BaseModel):
    model_id: str
    protected_class: str
    metrics: dict[str, Any]


class RedisWriteTool(BaseTool):
    name: str = "RedisWriteTool"
    description: str = "Writes computed fairness metrics to the Redis online feature store."
    args_schema: type[BaseModel] = RedisWriteInput

    def _run(self, model_id: str, protected_class: str, metrics: dict[str, Any]) -> str:
        try:
            import asyncio
            from sentinel.data.feature_store import FeatureStore

            async def _write():
                fs = FeatureStore()
                await fs.write_fairness_metrics(model_id, protected_class, metrics)

            asyncio.get_event_loop().run_until_complete(_write())
            return json.dumps({"status": "written", "model_id": model_id, "protected_class": protected_class})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SlackAlertInput(BaseModel):
    model_id: str
    alert_level: str
    message: str
    alert_type: str = "fairness"


class SlackAlertTool(BaseTool):
    name: str = "SlackAlertTool"
    description: str = "Sends formatted fairness alerts to Slack and creates alert records."
    args_schema: type[BaseModel] = SlackAlertInput

    def _run(self, model_id: str, alert_level: str, message: str, alert_type: str = "fairness") -> str:
        try:
            import asyncio
            from sentinel.notifications.slack import send_alert

            async def _send():
                return await send_alert(
                    model_id=model_id,
                    alert_type=alert_type,
                    alert_level=alert_level,
                    message=message,
                )

            result = asyncio.get_event_loop().run_until_complete(_send())
            return json.dumps({"status": "sent", "alert_id": result})
        except Exception as e:
            return json.dumps({"error": str(e)})


def create_auditor_agent() -> Agent:
    return Agent(
        role="Financial AI Fairness Auditor",
        goal=(
            "Continuously monitor all registered ML models for fairness violations across "
            "protected classes (age, sex, race, ethnicity, income bracket). Compute Demographic "
            "Parity Ratio, Equalized Odds Difference, and Disparate Impact Ratio. Fire alerts "
            "when thresholds are breached. Write all metrics to the Redis feature store."
        ),
        backstory=(
            "You are a rigorous AI fairness auditor with deep expertise in federal model risk "
            "management (SR 11-7), FCRA, and Regulation B requirements. You understand that "
            "biased financial advisor matching can cause material harm to consumers and expose "
            "the firm to regulatory action. You apply the highest standards of statistical "
            "rigor, including bootstrap confidence intervals, and escalate aggressively when "
            "fairness gaps appear."
        ),
        tools=[
            FairnessComputationTool(),
            MySQLQueryTool(),
            RedisWriteTool(),
            SlackAlertTool(),
        ],
        max_iter=settings.agent_max_tool_calls,
        verbose=True,
    )


def create_fairness_audit_task(agent: Agent, model_id: str) -> Task:
    return Task(
        description=(
            f"Perform a complete fairness audit for model {model_id}. "
            "Steps: (1) Query MySQL for the model's recent predictions using MySQLQueryTool. "
            "(2) Run FairnessComputationTool to compute all protected class metrics. "
            "(3) Write results to Redis using RedisWriteTool. "
            "(4) If any 'action' or 'watch' alert is found, send a Slack alert using SlackAlertTool. "
            "Return a structured JSON summary of all fairness metrics and alerts fired."
        ),
        expected_output=(
            "A JSON object containing: model_id, audit_timestamp, fairness_results (list of "
            "metrics per protected class), alerts_fired (list), overall_compliance_status."
        ),
        agent=agent,
    )
