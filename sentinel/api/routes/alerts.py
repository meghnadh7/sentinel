from __future__ import annotations
"""GET /alerts, POST approve — alert management and HITL."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.api.schemas import AlertApproveRequest, AlertResponse
from sentinel.data.database import get_db
from sentinel.data.models import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    model_id: Optional[str] = None,
    level: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    q = select(Alert).where(Alert.resolved_at.is_(None))
    if model_id:
        q = q.where(Alert.model_id == model_id)
    if level:
        q = q.where(Alert.alert_level == level)
    q = q.order_by(Alert.created_at.desc()).limit(100)
    result = await session.execute(q)
    alerts = result.scalars().all()
    return [
        AlertResponse(
            id=a.id,
            model_id=a.model_id,
            alert_type=a.alert_type,
            alert_level=a.alert_level,
            message=a.message,
            created_at=a.created_at,
            hitl_required=a.hitl_required,
            hitl_approved=a.hitl_approved,
            hitl_approved_by=a.hitl_approved_by,
            resolved_at=a.resolved_at,
        )
        for a in alerts
    ]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, session: AsyncSession = Depends(get_db)):
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse(
        id=alert.id,
        model_id=alert.model_id,
        alert_type=alert.alert_type,
        alert_level=alert.alert_level,
        message=alert.message,
        created_at=alert.created_at,
        hitl_required=alert.hitl_required,
        hitl_approved=alert.hitl_approved,
        hitl_approved_by=alert.hitl_approved_by,
        resolved_at=alert.resolved_at,
    )


@router.post("/{alert_id}/approve")
async def approve_alert(
    alert_id: str,
    request: AlertApproveRequest,
    session: AsyncSession = Depends(get_db),
):
    from sentinel.data.repositories.alerts import AlertRepository
    from sentinel.data.feature_store import FeatureStore

    repo = AlertRepository(session)
    alert = await repo.approve_hitl(alert_id, request.approved_by)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    fs = FeatureStore()
    await fs.set_hitl_approval(alert_id, approved=True)
    await session.commit()

    return {"status": "approved", "alert_id": alert_id, "approved_by": request.approved_by}


@router.post("/{alert_id}/reject")
async def reject_alert(
    alert_id: str,
    request: AlertApproveRequest,
    session: AsyncSession = Depends(get_db),
):
    from sentinel.data.feature_store import FeatureStore

    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.hitl_approved = False
    alert.hitl_approved_by = request.approved_by
    await session.flush()

    fs = FeatureStore()
    await fs.set_hitl_approval(alert_id, approved=False)
    await session.commit()

    return {"status": "rejected", "alert_id": alert_id, "rejected_by": request.approved_by}


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, session: AsyncSession = Depends(get_db)):
    from sentinel.data.repositories.alerts import AlertRepository

    repo = AlertRepository(session)
    alert = await repo.resolve(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await session.commit()
    return {"status": "resolved", "alert_id": alert_id}
