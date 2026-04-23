from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import FairnessMetric


class FairnessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, metric: FairnessMetric) -> FairnessMetric:
        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_latest_for_model(self, model_id: str) -> list[FairnessMetric]:
        from sqlalchemy import func
        subq = (
            select(
                FairnessMetric.protected_class,
                func.max(FairnessMetric.computed_at).label("max_ts"),
            )
            .where(FairnessMetric.model_id == model_id)
            .group_by(FairnessMetric.protected_class)
            .subquery()
        )
        q = select(FairnessMetric).join(
            subq,
            (FairnessMetric.protected_class == subq.c.protected_class)
            & (FairnessMetric.computed_at == subq.c.max_ts),
        ).where(FairnessMetric.model_id == model_id)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_history(self, model_id: str, limit: int = 100) -> list[FairnessMetric]:
        q = (
            select(FairnessMetric)
            .where(FairnessMetric.model_id == model_id)
            .order_by(FairnessMetric.computed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())
