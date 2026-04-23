from __future__ import annotations
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from fairlearn.metrics import MetricFrame, demographic_parity_ratio, equalized_odds_difference
from sklearn.metrics import accuracy_score

from sentinel.config import get_settings

settings = get_settings()

PROTECTED_CLASSES = ["sex", "race", "ethnicity", "age_bucket", "income_bracket"]


@dataclass
class FairnessResult:
    protected_class: str
    demographic_parity_ratio: float
    equalized_odds_diff: float
    disparate_impact_ratio: float
    sample_size: int
    alert_level: str  # none | watch | action
    dp_ratio_ci_lower: float
    dp_ratio_ci_upper: float
    subgroup_counts: dict[str, int] = field(default_factory=dict)


def _bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: np.ndarray,
    n_resamples: int = 1000,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """95% bootstrap CI for demographic parity ratio."""
    rng = np.random.default_rng(42)
    n = len(y_true)
    ratios = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        try:
            r = demographic_parity_ratio(y_true[idx], y_pred[idx], sensitive_features=sensitive[idx])
            if np.isfinite(r):
                ratios.append(r)
        except Exception:
            continue
    if not ratios:
        return float("nan"), float("nan")
    arr = np.array(ratios)
    return float(np.percentile(arr, 100 * alpha / 2)), float(np.percentile(arr, 100 * (1 - alpha / 2)))


def compute_fairness_metrics(
    predictions_df: pd.DataFrame,
    protected_class: str,
) -> FairnessResult | None:
    """Compute fairness metrics for a single protected class."""
    df = predictions_df.dropna(subset=[protected_class, "decision"])
    if len(df) < settings.fairness_min_subgroup_size:
        return None

    sensitive = df[protected_class].astype(str)
    y_pred_binary = (df["decision"].isin(["matched", "approved"])).astype(int).values
    y_true = np.ones(len(df), dtype=int)

    subgroup_counts = sensitive.value_counts().to_dict()
    min_subgroup = min(subgroup_counts.values()) if subgroup_counts else 0
    if min_subgroup < settings.fairness_min_subgroup_size:
        return None

    try:
        dp_ratio = demographic_parity_ratio(
            y_true, y_pred_binary, sensitive_features=sensitive
        )
    except Exception:
        dp_ratio = float("nan")

    try:
        eq_odds_diff = equalized_odds_difference(
            y_true, y_pred_binary, sensitive_features=sensitive
        )
    except Exception:
        eq_odds_diff = float("nan")

    # Disparate Impact Ratio (adverse impact ratio)
    try:
        mf = MetricFrame(
            metrics={"selection_rate": lambda yt, yp: yp.mean()},
            y_true=y_true,
            y_pred=y_pred_binary,
            sensitive_features=sensitive,
        )
        group_rates = mf.by_group["selection_rate"]
        di_ratio = float(group_rates.min() / group_rates.max()) if group_rates.max() > 0 else float("nan")
    except Exception:
        di_ratio = float("nan")

    ci_lower, ci_upper = _bootstrap_ci(y_true, y_pred_binary, sensitive.values)

    # Determine alert level
    if not np.isfinite(dp_ratio):
        alert_level = "none"
    elif dp_ratio < settings.fairness_demographic_parity_threshold:
        alert_level = "action"
    elif dp_ratio < settings.fairness_watch_threshold:
        alert_level = "watch"
    else:
        alert_level = "none"

    return FairnessResult(
        protected_class=protected_class,
        demographic_parity_ratio=float(dp_ratio) if np.isfinite(dp_ratio) else 0.0,
        equalized_odds_diff=float(eq_odds_diff) if np.isfinite(eq_odds_diff) else 0.0,
        disparate_impact_ratio=float(di_ratio) if np.isfinite(di_ratio) else 0.0,
        sample_size=len(df),
        alert_level=alert_level,
        dp_ratio_ci_lower=ci_lower,
        dp_ratio_ci_upper=ci_upper,
        subgroup_counts=subgroup_counts,
    )


def run_fairness_audit(predictions_df: pd.DataFrame) -> list[FairnessResult]:
    results = []
    for pc in PROTECTED_CLASSES:
        if pc not in predictions_df.columns:
            continue
        result = compute_fairness_metrics(predictions_df, pc)
        if result is not None:
            results.append(result)
    return results
