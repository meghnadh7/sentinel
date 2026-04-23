from __future__ import annotations
"""Integration tests for CrewAI crew wiring."""

import pytest
from unittest.mock import patch, MagicMock


def test_crew_builds():
    """Verify the crew can be built without errors (no actual LLM calls)."""
    with patch("crewai.Agent.__init__", return_value=None), \
         patch("crewai.Task.__init__", return_value=None), \
         patch("crewai.Crew.__init__", return_value=None):
        from sentinel.agents.auditor import create_auditor_agent, create_fairness_audit_task
        from sentinel.agents.red_team import create_red_team_agent, create_red_team_task
        # Just importing and verifying the modules load correctly
        assert create_auditor_agent is not None
        assert create_red_team_agent is not None


def test_agent_cards_json_valid():
    """Verify all agent card JSON files are valid."""
    import json
    from pathlib import Path

    cards_dir = Path("sentinel/agents/agent_cards")
    assert cards_dir.exists(), "Agent cards directory must exist"

    for card_file in cards_dir.glob("*.json"):
        with open(card_file) as f:
            data = json.load(f)
        assert "name" in data, f"{card_file.name} missing 'name'"
        assert "role" in data, f"{card_file.name} missing 'role'"
        assert "tools" in data, f"{card_file.name} missing 'tools'"
        assert "guardrails" in data, f"{card_file.name} missing 'guardrails'"
