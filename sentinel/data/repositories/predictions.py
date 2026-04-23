from __future__ import annotations
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import ModelPrediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_predictions_for_model(
        self,
        model_id: str,
        since: datetime | None = None,
        limit: int = 10000,
    ) -> list[ModelPrediction]:
        q = select(ModelPrediction).where(ModelPrediction.model_id == model_id)
        if since:
            q = q.where(ModelPrediction.timestamp >= since)
        q = q.order_by(ModelPrediction.timestamp.desc()).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def bulk_insert(self, predictions: list[ModelPrediction]) -> None:
        self.session.add_all(predictions)
        await self.session.flush()

    async def count_by_model(self, model_id: str) -> int:
        from sqlalchemy import func, select
        result = await self.session.execute(
            select(func.count()).where(ModelPrediction.model_id == model_id)
        )
        return result.scalar_one()
