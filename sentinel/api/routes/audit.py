from __future__ import annotations
"""POST /audit/{model_id} — trigger audit pipeline."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.api.schemas import AuditRequest, AuditResponse
from sentinel.data.audit_log import append_audit_entry
from sentinel.data.database import get_db

router = APIRouter(prefix="/audit", tags=["audit"])

_executor = ThreadPoolExecutor(max_workers=2)


async def _run_audit_background(model_id: str, trigger: str) -> None:
    from sentinel.config import get_settings
    from sentinel.data.database import AsyncSessionLocal

    settings = get_settings()

    async with AsyncSessionLocal() as session:
        await append_audit_entry(
            session,
            agent_name="api",
            action="audit_triggered",
            model_id=model_id,
            result={"trigger": trigger},
        )
        await session.commit()

    try:
        if settings.use_mock_llm:
            from sentinel.mock_llm import mock_run_full_audit
            await asyncio.sleep(0.1)
            mock_run_full_audit(model_id)
        else:
            from sentinel.agents.crew import build_audit_crew
            loop = asyncio.get_event_loop()
            crew = build_audit_crew(model_id)
            await loop.run_in_executor(_executor, crew.kickoff)

        async with AsyncSessionLocal() as session:
            await append_audit_entry(
                session,
                agent_name="api",
                action="audit_completed",
                model_id=model_id,
                result={"trigger": trigger, "status": "success"},
            )
            await session.commit()
    except Exception as e:
        async with AsyncSessionLocal() as session:
            await append_audit_entry(
                session,
                agent_name="api",
                action="audit_failed",
                model_id=model_id,
                result={"error": str(e)},
            )
            await session.commit()


@router.post("/{model_id}", response_model=AuditResponse)
async def trigger_audit(
    model_id: str,
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    from sentinel.data.models import Model
    model = await session.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    audit_id = str(uuid.uuid4())
    background_tasks.add_task(
        _run_audit_background, model_id, request.trigger
    )

    return AuditResponse(
        model_id=model_id,
        audit_id=audit_id,
        status="queued",
        message=f"Audit queued for {model.name} (trigger: {request.trigger}). "
                "Results will be available in the database shortly.",
    )


@router.get("/chain/verify")
async def verify_audit_chain(session: AsyncSession = Depends(get_db)):
    from sentinel.data.audit_log import verify_audit_chain as _verify
    is_valid, total, errors = await _verify(session)
    return {
        "chain_valid": is_valid,
        "total_entries": total,
        "errors": errors[:10] if errors else [],
        "message": "chain intact: 100% valid" if is_valid else f"COMPROMISED — {len(errors)} errors",
    }
