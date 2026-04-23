from __future__ import annotations
"""Unit tests for red team logic."""

import pytest

from sentinel.audit.red_team_attacks import (
    OWASP_LLM_CATEGORIES,
    SANDBOX_ALLOWLIST,
    _check_sandbox_url,
)


def test_sandbox_allowlist_accepts_valid_url():
    assert _check_sandbox_url("http://localhost:8000/sandbox/advisor-rag/v1") is True
    assert _check_sandbox_url("/sandbox/test") is True


def test_sandbox_allowlist_rejects_production_url():
    assert _check_sandbox_url("http://localhost:8000/api/models") is False
    assert _check_sandbox_url("https://production.datalign.com/api") is False
    assert _check_sandbox_url("http://external-service.com/sandbox/") is False


def test_owasp_categories_populated():
    assert "prompt_injection" in OWASP_LLM_CATEGORIES
    assert "LLM01" in OWASP_LLM_CATEGORIES["prompt_injection"]


def test_sandbox_allowlist_not_empty():
    assert len(SANDBOX_ALLOWLIST) > 0
