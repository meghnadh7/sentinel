from __future__ import annotations
"""GET /models — model registry and compliance status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.api.schemas import (
    ComplianceStatusResponse,
    GovernanceGateResponse,
    ModelListResponse,
    ModelResponse,
)
from sentinel.data.database import get_db
from sentinel.data.models import Alert, FairnessMetric, GovernanceGate, Model, ModelCard

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
async def list_models(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Model).order_by(Model.created_at.desc()))
    models = result.scalars().all()
    return ModelListResponse(
        models=[
            ModelResponse(
                id=m.id,
                name=m.name,
                version=m.version,
                risk_tier=m.risk_tier,
                validation_status=m.validation_status,
                mlflow_run_id=m.mlflow_run_id,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ],
        total=len(models),
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str, session: AsyncSession = Depends(get_db)):
    model = await session.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        risk_tier=model.risk_tier,
        validation_status=model.validation_status,
        mlflow_run_id=model.mlflow_run_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/{model_id}/compliance", response_model=ComplianceStatusResponse)
async def get_compliance_status(model_id: str, session: AsyncSession = Depends(get_db)):
    model = await session.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Count fairness alerts
    fa_result = await session.execute(
        select(FairnessMetric)
        .where(FairnessMetric.model_id == model_id)
        .where(FairnessMetric.alert_level != "none")
    )
    fairness_alerts = fa_result.scalars().all()

    # Count open action alerts
    alert_result = await session.execute(
        select(Alert)
        .where(Alert.model_id == model_id)
        .where(Alert.alert_level == "action")
        .where(Alert.resolved_at.is_(None))
    )
    action_alerts = alert_result.scalars().all()

    # Latest model card completeness
    card_result = await session.execute(
        select(ModelCard)
        .where(ModelCard.model_id == model_id)
        .order_by(ModelCard.version.desc())
        .limit(1)
    )
    card = card_result.scalar_one_or_none()

    # Latest governance gate
    gate_result = await session.execute(
        select(GovernanceGate)
        .where(GovernanceGate.model_id == model_id)
        .order_by(GovernanceGate.checked_at.desc())
        .limit(1)
    )
    gate = gate_result.scalar_one_or_none()

    gate_response = None
    if gate:
        gate_response = GovernanceGateResponse(
            model_id=model_id,
            fairness_gate_passed=gate.fairness_gate_passed,
            robustness_gate_passed=gate.robustness_gate_passed,
            explainability_gate_passed=gate.explainability_gate_passed,
            documentation_gate_passed=gate.documentation_gate_passed,
            all_gates_passed=gate.all_gates_passed,
            promotion_blocked=gate.promotion_blocked,
        )

    return ComplianceStatusResponse(
        model_id=model_id,
        model_name=model.name,
        risk_tier=model.risk_tier,
        validation_status=model.validation_status,
        fairness_alert_count=len(fairness_alerts),
        open_action_alerts=len(action_alerts),
        latest_completeness_score=card.completeness_score if card else None,
        governance_gate_status=gate_response,
    )
