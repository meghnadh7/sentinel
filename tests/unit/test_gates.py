from __future__ import annotations
"""Unit tests for governance gates."""

import pytest

from sentinel.compliance.gates import GovernanceGateChecker, GateResult


def test_all_gates_pass():
    checker = GovernanceGateChecker()
    result = checker.check_all(
        fairness_ok=True,
        robustness_ok=True,
        explainability_ok=True,
        documentation_ok=True,
    )
    assert result.all_passed is True
    assert result.promotion_blocked is False


def test_one_gate_fails():
    checker = GovernanceGateChecker()
    result = checker.check_all(
        fairness_ok=False,
        robustness_ok=True,
        explainability_ok=True,
        documentation_ok=True,
    )
    assert result.all_passed is False
    assert result.promotion_blocked is True
    assert "fairness" in result.failed_gates


def test_multiple_gates_fail():
    checker = GovernanceGateChecker()
    result = checker.check_all(
        fairness_ok=False,
        robustness_ok=False,
        explainability_ok=True,
        documentation_ok=True,
    )
    assert result.all_passed is False
    assert len(result.failed_gates) == 2


def test_gate_result_summary():
    checker = GovernanceGateChecker()
    result = checker.check_all(
        fairness_ok=True,
        robustness_ok=True,
        explainability_ok=True,
        documentation_ok=True,
    )
    summary = result.to_dict()
    assert "all_gates_passed" in summary
    assert summary["all_gates_passed"] is True
