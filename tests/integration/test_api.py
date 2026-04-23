from __future__ import annotations
"""Integration tests for the FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from sentinel.api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_models_list(client: AsyncClient):
    resp = await client.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_alerts_list(client: AsyncClient):
    resp = await client.get("/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_model_not_found(client: AsyncClient):
    resp = await client.get("/models/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_chain_verify(client: AsyncClient):
    resp = await client.get("/audit/chain/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "chain_valid" in data
    assert "total_entries" in data


@pytest.mark.asyncio
async def test_agent_cards(client: AsyncClient):
    resp = await client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
