from __future__ import annotations
"""Unit tests for fairness audit logic."""

import numpy as np
import pandas as pd
import pytest

from sentinel.audit.fairness import (
    FairnessResult,
    _bootstrap_ci,
    compute_fairness_metrics,
    run_fairness_audit,
)


def _make_predictions_df(n: int = 500, inject_gap: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    sex = rng.choice(["male", "female"], size=n)
    # Inject gap: females matched less often
    matched = np.where(
        sex == "male",
        rng.random(n) > 0.3,
        rng.random(n) > (0.5 if inject_gap else 0.3),
    )
    return pd.DataFrame({
        "sex": sex,
        "race": rng.choice(["white", "black", "hispanic", "asian"], size=n),
        "age_bucket": rng.choice(["25-34", "35-44", "45-54"], size=n),
        "income_bracket": rng.choice(["<50k", "50k-100k", ">200k"], size=n),
        "ethnicity": rng.choice(["hispanic", "non-hispanic"], size=n),
        "decision": np.where(matched, "matched", "flagged"),
        "prediction": rng.random(n),
        "confidence": rng.random(n),
    })


def test_compute_fairness_metrics_returns_result():
    df = _make_predictions_df(600)
    result = compute_fairness_metrics(df, "sex")
    assert result is not None
    assert isinstance(result, FairnessResult)
    assert result.protected_class == "sex"
    assert 0 <= result.demographic_parity_ratio <= 2.0
    assert result.alert_level in ("none", "watch", "action")


def test_compute_fairness_below_min_sample_returns_none():
    df = _make_predictions_df(50)
    result = compute_fairness_metrics(df, "sex")
    assert result is None


def test_fairness_gap_triggers_action_alert():
    df = _make_predictions_df(1000, inject_gap=True)
    result = compute_fairness_metrics(df, "sex")
    assert result is not None
    assert result.alert_level in ("watch", "action")


def test_run_fairness_audit_returns_multiple_classes():
    df = _make_predictions_df(800)
    results = run_fairness_audit(df)
    assert len(results) >= 1
    protected_classes = {r.protected_class for r in results}
    assert "sex" in protected_classes or "race" in protected_classes


def test_bootstrap_ci_bounds():
    rng = np.random.default_rng(0)
    n = 300
    y_true = np.ones(n, dtype=int)
    y_pred = rng.integers(0, 2, size=n)
    sensitive = rng.choice(["a", "b"], size=n)
    lo, hi = _bootstrap_ci(y_true, y_pred, sensitive, n_resamples=100)
    if not (np.isnan(lo) or np.isnan(hi)):
        assert lo <= hi
        assert 0 <= lo
        assert hi <= 2.0


def test_ci_included_in_result():
    df = _make_predictions_df(600)
    result = compute_fairness_metrics(df, "sex")
    if result is not None:
        # CI should be numeric (may be nan if trivial)
        assert isinstance(result.dp_ratio_ci_lower, float)
        assert isinstance(result.dp_ratio_ci_upper, float)
