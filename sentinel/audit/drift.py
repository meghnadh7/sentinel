from __future__ import annotations
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


@dataclass
class DriftResult:
    feature: str
    ks_statistic: float
    p_value: float
    drift_detected: bool
    drift_threshold: float = 0.05


def detect_feature_drift(
    reference: pd.Series,
    current: pd.Series,
    significance_level: float = 0.05,
) -> DriftResult:
    """Kolmogorov-Smirnov test for distribution drift."""
    ref_vals = reference.dropna().values
    cur_vals = current.dropna().values

    if len(ref_vals) < 10 or len(cur_vals) < 10:
        return DriftResult(
            feature=reference.name or "unknown",
            ks_statistic=0.0,
            p_value=1.0,
            drift_detected=False,
        )

    stat, p_value = ks_2samp(ref_vals, cur_vals)
    return DriftResult(
        feature=str(reference.name),
        ks_statistic=float(stat),
        p_value=float(p_value),
        drift_detected=p_value < significance_level,
        drift_threshold=significance_level,
    )


def run_drift_detection(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    numeric_features: list[str],
    significance_level: float = 0.05,
) -> list[DriftResult]:
    results = []
    for feature in numeric_features:
        if feature in reference_df.columns and feature in current_df.columns:
            result = detect_feature_drift(
                reference_df[feature],
                current_df[feature],
                significance_level,
            )
            results.append(result)
    return results


def summarize_drift(results: list[DriftResult]) -> dict:
    drifted = [r for r in results if r.drift_detected]
    return {
        "total_features_checked": len(results),
        "drifted_features": len(drifted),
        "drift_fraction": len(drifted) / len(results) if results else 0.0,
        "drifted_feature_names": [r.feature for r in drifted],
        "max_ks_statistic": max((r.ks_statistic for r in results), default=0.0),
    }
