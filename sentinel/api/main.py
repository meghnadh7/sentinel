from __future__ import annotations
"""FastAPI app entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sentinel.api.routes import agent_cards, alerts, audit, models, red_team
from sentinel.config import get_settings
from sentinel.data.database import create_tables
from sentinel.observability.metrics import setup_prometheus
from sentinel.observability.tracing import setup_tracing

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    setup_tracing(app)
    setup_prometheus()
    yield


app = FastAPI(
    title="Sentinel API",
    description="Continuous AI audit and red-teaming platform for financial advisory services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(audit.router)
app.include_router(alerts.router)
app.include_router(red_team.router)
app.include_router(agent_cards.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sentinel-api", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "service": "Sentinel",
        "description": "Continuous AI audit platform for financial advisory services",
        "docs": "/docs",
        "health": "/health",
    }
