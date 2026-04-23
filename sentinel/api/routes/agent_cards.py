from __future__ import annotations
"""GET /.well-known/agent-card.json — agent cards endpoint."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["agent-cards"])

AGENT_CARDS_DIR = Path(__file__).parent.parent.parent / "agents" / "agent_cards"


@router.get("/.well-known/agent-card.json")
async def get_all_agent_cards():
    cards = {}
    for card_file in AGENT_CARDS_DIR.glob("*.json"):
        with open(card_file) as f:
            cards[card_file.stem] = json.load(f)
    return {"agents": cards, "platform": "sentinel", "version": "1.0.0"}


@router.get("/.well-known/agent-cards/{agent_name}.json")
async def get_agent_card(agent_name: str):
    card_path = AGENT_CARDS_DIR / f"{agent_name}.json"
    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent card not found: {agent_name}")
    with open(card_path) as f:
        return json.load(f)
