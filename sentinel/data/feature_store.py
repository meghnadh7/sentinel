from __future__ import annotations
import json
from typing import Any

import redis.asyncio as aioredis

from sentinel.config import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class FeatureStore:
    """Redis-backed online compliance signal store."""

    def __init__(self, client: aioredis.Redis | None = None) -> None:
        self.client = client or get_redis()

    def _fairness_key(self, model_id: str, protected_class: str) -> str:
        return f"sentinel:fairness:{model_id}:{protected_class}"

    def _shap_key(self, model_id: str) -> str:
        return f"sentinel:shap:{model_id}"

    def _campaign_key(self, campaign_id: str) -> str:
        return f"sentinel:campaign:{campaign_id}"

    async def write_fairness_metrics(
        self,
        model_id: str,
        protected_class: str,
        metrics: dict[str, Any],
        ttl_seconds: int = 7200,
    ) -> None:
        key = self._fairness_key(model_id, protected_class)
        await self.client.set(key, json.dumps(metrics), ex=ttl_seconds)

    async def read_fairness_metrics(
        self, model_id: str, protected_class: str
    ) -> dict[str, Any] | None:
        key = self._fairness_key(model_id, protected_class)
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def write_shap_stability(
        self, model_id: str, data: dict[str, Any], ttl_seconds: int = 86400
    ) -> None:
        await self.client.set(self._shap_key(model_id), json.dumps(data), ex=ttl_seconds)

    async def read_shap_stability(self, model_id: str) -> dict[str, Any] | None:
        data = await self.client.get(self._shap_key(model_id))
        return json.loads(data) if data else None

    async def write_campaign_status(
        self, campaign_id: str, status: dict[str, Any], ttl_seconds: int = 3600
    ) -> None:
        await self.client.set(self._campaign_key(campaign_id), json.dumps(status), ex=ttl_seconds)

    async def read_campaign_status(self, campaign_id: str) -> dict[str, Any] | None:
        data = await self.client.get(self._campaign_key(campaign_id))
        return json.loads(data) if data else None

    async def set_hitl_approval(self, alert_id: str, approved: bool) -> None:
        key = f"sentinel:hitl:{alert_id}"
        await self.client.set(key, "approved" if approved else "rejected", ex=86400)

    async def get_hitl_approval(self, alert_id: str) -> str | None:
        return await self.client.get(f"sentinel:hitl:{alert_id}")

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False
