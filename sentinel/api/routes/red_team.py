from __future__ import annotations
"""POST /red-team/campaign — red team campaign management."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.api.schemas import RedTeamCampaignRequest, RedTeamCampaignResponse
from sentinel.data.database import get_db
from sentinel.data.models import Model, RedTeamCampaign

router = APIRouter(prefix="/red-team", tags=["red-team"])
UTC = timezone.utc

_executor = ThreadPoolExecutor(max_workers=2)


async def _run_campaign_background(campaign_id: str, model_id: str, campaign_type: str, n_attacks: int) -> None:
    from sentinel.audit.red_team_attacks import RedTeamEngine
    from sentinel.data.database import AsyncSessionLocal

    engine = RedTeamEngine()

    if campaign_type == "prompt_injection":
        result = await engine.run_prompt_injection_campaign(
            campaign_id=campaign_id,
            model_id=model_id,
            n_attacks=n_attacks,
        )
    else:
        result = None

    async with AsyncSessionLocal() as session:
        campaign = await session.get(RedTeamCampaign, campaign_id)
        if campaign and result:
            campaign.total_attacks = result.total_attacks
            campaign.successful_attacks = result.successful_attacks
            campaign.attack_success_rate = result.attack_success_rate
            campaign.llm_cost_dollars = result.llm_cost_dollars
            campaign.status = result.status
            campaign.completed_at = datetime.now(UTC)
            await session.commit()


@router.post("/campaign", response_model=RedTeamCampaignResponse)
async def launch_campaign(
    request: RedTeamCampaignRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    model = await session.get(Model, request.model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    campaign_id = str(uuid.uuid4())
    campaign = RedTeamCampaign(
        id=campaign_id,
        model_id=request.model_id,
        campaign_type=request.campaign_type,
        status="running",
    )
    session.add(campaign)
    await session.commit()

    background_tasks.add_task(
        _run_campaign_background,
        campaign_id, request.model_id, request.campaign_type, request.n_attacks,
    )

    return RedTeamCampaignResponse(
        campaign_id=campaign_id,
        model_id=request.model_id,
        status="running",
        total_attacks=0,
        successful_attacks=0,
        attack_success_rate=None,
        message=f"Red team campaign started for {model.name}",
    )


@router.get("/campaigns/{model_id}", response_model=list[RedTeamCampaignResponse])
async def list_campaigns(model_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(RedTeamCampaign)
        .where(RedTeamCampaign.model_id == model_id)
        .order_by(RedTeamCampaign.started_at.desc())
    )
    campaigns = result.scalars().all()
    return [
        RedTeamCampaignResponse(
            campaign_id=c.id,
            model_id=c.model_id,
            status=c.status,
            total_attacks=c.total_attacks,
            successful_attacks=c.successful_attacks,
            attack_success_rate=c.attack_success_rate,
            message=c.status,
        )
        for c in campaigns
    ]
