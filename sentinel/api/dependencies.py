from __future__ import annotations
"""FastAPI dependencies."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.data.database import get_db
from sentinel.data.feature_store import FeatureStore


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncGenerator[AsyncSession, None]:
    yield session


def get_feature_store() -> FeatureStore:
    return FeatureStore()
