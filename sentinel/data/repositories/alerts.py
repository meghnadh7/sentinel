from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import Alert

UTC = timezone.utc


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, alert: Alert) -> Alert:
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def get_open_alerts(self, model_id: str | None = None) -> list[Alert]:
        q = select(Alert).where(Alert.resolved_at.is_(None))
        if model_id:
            q = q.where(Alert.model_id == model_id)
        q = q.order_by(Alert.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, alert_id: str) -> Alert | None:
        result = await self.session.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def approve_hitl(self, alert_id: str, approved_by: str) -> Alert | None:
        alert = await self.get_by_id(alert_id)
        if alert:
            alert.hitl_approved = True
            alert.hitl_approved_by = approved_by
            alert.hitl_approved_at = datetime.now(UTC)
            await self.session.flush()
        return alert

    async def resolve(self, alert_id: str) -> Alert | None:
        alert = await self.get_by_id(alert_id)
        if alert:
            alert.resolved_at = datetime.now(UTC)
            await self.session.flush()
        return alert
