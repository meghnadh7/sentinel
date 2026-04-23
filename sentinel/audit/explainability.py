from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr

from sentinel.config import get_settings

settings = get_settings()


@dataclass
class SHAPResult:
    feature_importance: dict[str, float]
    spearman_rho: float | None
    baseline_rho: float | None
    stability_alert: bool
    n_samples: int
    top_features: list[tuple[str, float]]


def compute_shap_importance(
    model: Any,
    X: np.ndarray,
    feature_names: list[str],
    max_samples: int = 500,
) -> dict[str, float]:
    """Compute mean absolute SHAP values as feature importance."""
    if len(X) > max_samples:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(X), size=max_samples, replace=False)
        X = X[idx]

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
    except Exception:
        try:
            background = shap.sample(X, min(100, len(X)))
            explainer = shap.KernelExplainer(model.predict, background)
            shap_values = explainer.shap_values(X, nsamples=50)
        except Exception:
            return {name: 0.0 for name in feature_names}

    if isinstance(shap_values, list):
        # older SHAP: list of per-class 2D arrays (n_samples, n_features)
        shap_arr = np.mean(np.abs(np.array(shap_values)), axis=0)  # → (n_samples, n_features)
        mean_abs = shap_arr.mean(axis=0)  # → (n_features,)
    else:
        shap_arr = np.abs(np.asarray(shap_values))
        if shap_arr.ndim == 3:
            # newer SHAP: (n_samples, n_features, n_classes)
            mean_abs = shap_arr.mean(axis=(0, 2))  # → (n_features,)
        elif shap_arr.ndim == 2:
            # (n_samples, n_features)
            mean_abs = shap_arr.mean(axis=0)  # → (n_features,)
        else:
            mean_abs = shap_arr

    return {name: float(v) for name, v in zip(feature_names, mean_abs)}


def compute_spearman_stability(
    current_importance: dict[str, float],
    baseline_importance: dict[str, float],
) -> float:
    """Compute Spearman rank correlation between current and baseline SHAP rankings."""
    features = sorted(set(current_importance.keys()) & set(baseline_importance.keys()))
    if len(features) < 2:
        return 1.0

    current_vals = [current_importance[f] for f in features]
    baseline_vals = [baseline_importance[f] for f in features]

    rho, _ = spearmanr(current_vals, baseline_vals)
    return float(rho) if np.isfinite(rho) else 1.0


def run_shap_analysis(
    model: Any,
    X: np.ndarray,
    feature_names: list[str],
    baseline_importance: dict[str, float] | None = None,
) -> SHAPResult:
    importance = compute_shap_importance(model, X, feature_names)

    spearman_rho = None
    stability_alert = False
    if baseline_importance:
        spearman_rho = compute_spearman_stability(importance, baseline_importance)
        stability_alert = spearman_rho < settings.shap_stability_threshold

    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

    return SHAPResult(
        feature_importance=importance,
        spearman_rho=spearman_rho,
        baseline_rho=None,
        stability_alert=stability_alert,
        n_samples=len(X),
        top_features=top_features,
    )
