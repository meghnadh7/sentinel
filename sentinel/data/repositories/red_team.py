from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import RedTeamAttack, RedTeamCampaign


class RedTeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_campaign(self, campaign: RedTeamCampaign) -> RedTeamCampaign:
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def update_campaign(self, campaign: RedTeamCampaign) -> RedTeamCampaign:
        await self.session.merge(campaign)
        await self.session.flush()
        return campaign

    async def save_attack(self, attack: RedTeamAttack) -> RedTeamAttack:
        self.session.add(attack)
        await self.session.flush()
        return attack

    async def get_campaigns_for_model(self, model_id: str) -> list[RedTeamCampaign]:
        q = (
            select(RedTeamCampaign)
            .where(RedTeamCampaign.model_id == model_id)
            .order_by(RedTeamCampaign.started_at.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_campaign_by_id(self, campaign_id: str) -> RedTeamCampaign | None:
        result = await self.session.execute(
            select(RedTeamCampaign).where(RedTeamCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
