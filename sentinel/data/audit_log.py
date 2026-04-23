from __future__ import annotations
import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

UTC = timezone.utc

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.models import AuditLog


_GENESIS_HASH = "0" * 64

# In-memory last hash + lock to serialize concurrent chain writes.
# On startup, we re-hydrate from the DB (see _ensure_hydrated).
_chain_lock = asyncio.Lock()
_last_hash: str | None = None  # None = not yet hydrated


def _compute_hash(entry_id: str, timestamp: str, agent_name: str, action: str,
                  model_id: str | None, result: Any, previous_hash: str) -> str:
    # timestamp excluded: MySQL TIMESTAMP has no sub-second precision and returns
    # naive datetimes, making it unreliable as hash input. Chain integrity is
    # guaranteed by previous_hash; entry_id provides per-entry uniqueness.
    payload = json.dumps({
        "entry_id": entry_id,
        "agent_name": agent_name,
        "action": action,
        "model_id": model_id,
        "result": result,
        "previous_hash": previous_hash,
    }, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


async def _get_latest_hash_from_db(session: AsyncSession) -> str:
    result = await session.execute(
        select(AuditLog.current_hash).order_by(AuditLog.id.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row is not None else _GENESIS_HASH


async def append_audit_entry(
    session: AsyncSession,
    agent_name: str,
    action: str,
    model_id: str | None = None,
    result: dict[str, Any] | None = None,
) -> AuditLog:
    global _last_hash

    async with _chain_lock:
        # Hydrate from DB on first call (handles restarts).
        if _last_hash is None:
            _last_hash = await _get_latest_hash_from_db(session)

        previous_hash = _last_hash
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC)

        current_hash = _compute_hash(
            entry_id=entry_id,
            timestamp="",
            agent_name=agent_name,
            action=action,
            model_id=model_id,
            result=result,
            previous_hash=previous_hash,
        )

        entry = AuditLog(
            entry_id=entry_id,
            timestamp=timestamp,
            agent_name=agent_name,
            action=action,
            model_id=model_id,
            result=result,
            previous_hash=previous_hash,
            current_hash=current_hash,
        )
        session.add(entry)
        await session.flush()

        # Update in-memory pointer immediately (before commit) so the next
        # concurrent caller sees the correct previous_hash even if this
        # session hasn't committed yet.
        _last_hash = current_hash

    return entry


async def verify_audit_chain(session: AsyncSession) -> tuple[bool, int, list[str]]:
    """Verify the full hash chain. Returns (is_valid, total_entries, errors)."""
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.id.asc())
    )
    entries = result.scalars().all()

    errors: list[str] = []
    previous_hash = _GENESIS_HASH

    for entry in entries:
        if entry.previous_hash != previous_hash:
            errors.append(
                f"Entry {entry.entry_id}: broken chain — expected previous_hash "
                f"{previous_hash[:16]}... got {entry.previous_hash[:16]}..."
            )

        expected_hash = _compute_hash(
            entry_id=entry.entry_id,
            timestamp="",
            agent_name=entry.agent_name,
            action=entry.action,
            model_id=entry.model_id,
            result=entry.result,
            previous_hash=entry.previous_hash,
        )
        if entry.current_hash != expected_hash:
            errors.append(
                f"Entry {entry.entry_id}: hash mismatch — stored {entry.current_hash[:16]}... "
                f"computed {expected_hash[:16]}..."
            )

        previous_hash = entry.current_hash

    is_valid = len(errors) == 0
    return is_valid, len(entries), errors
