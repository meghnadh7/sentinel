from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import ModelCard


class ModelCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, card: ModelCard) -> ModelCard:
        self.session.add(card)
        await self.session.flush()
        return card

    async def get_latest_for_model(self, model_id: str) -> ModelCard | None:
        result = await self.session.execute(
            select(ModelCard)
            .where(ModelCard.model_id == model_id)
            .order_by(ModelCard.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_version(self, model_id: str) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.max(ModelCard.version)).where(ModelCard.model_id == model_id)
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def list_for_model(self, model_id: str) -> list[ModelCard]:
        result = await self.session.execute(
            select(ModelCard)
            .where(ModelCard.model_id == model_id)
            .order_by(ModelCard.version.desc())
        )
        return list(result.scalars().all())
