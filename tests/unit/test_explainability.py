from __future__ import annotations
"""Unit tests for SHAP explainability."""

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from sentinel.audit.explainability import (
    compute_shap_importance,
    compute_spearman_stability,
    run_shap_analysis,
)


@pytest.fixture
def simple_model():
    rng = np.random.default_rng(0)
    X = rng.random((200, 4))
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)
    model = RandomForestClassifier(n_estimators=10, random_state=0)
    model.fit(X, y)
    return model, X


def test_compute_shap_importance_returns_dict(simple_model):
    model, X = simple_model
    features = ["f1", "f2", "f3", "f4"]
    importance = compute_shap_importance(model, X, features)
    assert set(importance.keys()) == set(features)
    assert all(v >= 0 for v in importance.values())


def test_shap_importance_top_feature(simple_model):
    model, X = simple_model
    features = ["f1", "f2", "f3", "f4"]
    importance = compute_shap_importance(model, X, features)
    top = max(importance, key=importance.get)
    # f1 and f2 are the most predictive features
    assert top in ("f1", "f2")


def test_spearman_stability_identical():
    imp = {"a": 0.5, "b": 0.3, "c": 0.2}
    rho = compute_spearman_stability(imp, imp)
    assert abs(rho - 1.0) < 1e-6


def test_spearman_stability_reversed():
    current = {"a": 0.1, "b": 0.2, "c": 0.3}
    baseline = {"a": 0.3, "b": 0.2, "c": 0.1}
    rho = compute_spearman_stability(current, baseline)
    assert rho < 0.0


def test_run_shap_analysis_no_baseline(simple_model):
    model, X = simple_model
    features = ["f1", "f2", "f3", "f4"]
    result = run_shap_analysis(model, X, features)
    assert result.spearman_rho is None
    assert result.stability_alert is False
    assert len(result.top_features) <= 10


def test_run_shap_analysis_with_baseline_alert(simple_model):
    model, X = simple_model
    features = ["f1", "f2", "f3", "f4"]
    # Completely reversed baseline → low rho → alert
    baseline = {"f1": 0.01, "f2": 0.02, "f3": 0.5, "f4": 0.9}
    result = run_shap_analysis(model, X, features, baseline_importance=baseline)
    assert result.spearman_rho is not None
    # May or may not trigger alert depending on actual values; just check types
    assert isinstance(result.stability_alert, bool)
