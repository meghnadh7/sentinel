from __future__ import annotations
"""Unit tests for hash-chained audit log."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sentinel.data.audit_log import (
    _GENESIS_HASH,
    _compute_hash,
    append_audit_entry,
    verify_audit_chain,
)
from sentinel.data.models import AuditLog


def test_compute_hash_deterministic():
    h1 = _compute_hash("id1", "2024-01-01T00:00:00", "auditor", "test", "m1", None, _GENESIS_HASH)
    h2 = _compute_hash("id1", "2024-01-01T00:00:00", "auditor", "test", "m1", None, _GENESIS_HASH)
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_changes_with_input():
    h1 = _compute_hash("id1", "2024-01-01T00:00:00", "auditor", "test", "m1", None, _GENESIS_HASH)
    h2 = _compute_hash("id2", "2024-01-01T00:00:00", "auditor", "test", "m1", None, _GENESIS_HASH)
    assert h1 != h2


def test_compute_hash_result_included():
    h1 = _compute_hash("id1", "ts", "a", "act", None, {"score": 0.9}, "prev")
    h2 = _compute_hash("id1", "ts", "a", "act", None, {"score": 0.8}, "prev")
    assert h1 != h2


@pytest.mark.asyncio
async def test_append_audit_entry_chain():
    """Test that entries chain correctly via mock session."""
    from datetime import datetime, timezone
    UTC = timezone.utc

    entries_added = []

    class FakeResult:
        def scalar_one_or_none(self):
            if not entries_added:
                return None
            return entries_added[-1].current_hash

    class FakeSession:
        async def execute(self, query):
            return FakeResult()

        def add(self, entry):
            entries_added.append(entry)

        async def flush(self):
            pass

    session = FakeSession()

    entry1 = await append_audit_entry(session, "auditor", "compute_fairness", "model-1")
    assert entry1.previous_hash == _GENESIS_HASH
    assert len(entry1.current_hash) == 64

    entry2 = await append_audit_entry(session, "red_team", "run_campaign", "model-1")
    assert entry2.previous_hash == entry1.current_hash
    assert entry2.current_hash != entry1.current_hash


@pytest.mark.asyncio
async def test_verify_chain_empty():
    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class FakeSession:
        async def execute(self, query):
            return FakeResult()

    is_valid, total, errors = await verify_audit_chain(FakeSession())
    assert is_valid is True
    assert total == 0
    assert errors == []


@pytest.mark.asyncio
async def test_verify_chain_tampered():
    from datetime import datetime, timezone
    UTC = timezone.utc

    ts = datetime.now(UTC)

    h0 = _GENESIS_HASH
    h1 = _compute_hash("e1", ts.isoformat(), "auditor", "act1", "m1", None, h0)
    h2 = _compute_hash("e2", ts.isoformat(), "auditor", "act2", "m1", None, h1)

    entry1 = MagicMock(spec=AuditLog)
    entry1.entry_id = "e1"
    entry1.timestamp = ts
    entry1.agent_name = "auditor"
    entry1.action = "act1"
    entry1.model_id = "m1"
    entry1.result = None
    entry1.previous_hash = h0
    entry1.current_hash = h1

    entry2 = MagicMock(spec=AuditLog)
    entry2.entry_id = "e2"
    entry2.timestamp = ts
    entry2.agent_name = "auditor"
    entry2.action = "act2"
    entry2.model_id = "m1"
    entry2.result = None
    entry2.previous_hash = "tampered_hash"  # broken chain
    entry2.current_hash = h2

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [entry1, entry2]

    class FakeSession:
        async def execute(self, query):
            return FakeResult()

    is_valid, total, errors = await verify_audit_chain(FakeSession())
    assert is_valid is False
    assert total == 2
    assert len(errors) >= 1
