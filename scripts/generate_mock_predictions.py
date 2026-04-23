from __future__ import annotations
#!/usr/bin/env python3
"""Insert mock prediction logs into MySQL with realistic distributions."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, ".")

from sentinel.data.database import AsyncSessionLocal
from sentinel.data.models import ModelPrediction

UTC = timezone.utc
rng = np.random.default_rng(123)

AGE_BUCKETS = ["25-34", "35-44", "45-54", "55-64", "65-75"]
SEX_VALUES = ["male", "female"]
RACE_VALUES = ["white", "black", "hispanic", "asian", "other"]
INCOME_BRACKETS = ["<50k", "50k-100k", "100k-200k", ">200k"]
DECISIONS = ["matched", "flagged"]


def _age_bucket(age: float) -> str:
    if age < 35:
        return "25-34"
    elif age < 45:
        return "35-44"
    elif age < 55:
        return "45-54"
    elif age < 65:
        return "55-64"
    else:
        return "65-75"


def _income_bracket(income: float) -> str:
    if income < 50_000:
        return "<50k"
    elif income < 100_000:
        return "50k-100k"
    elif income < 200_000:
        return "100k-200k"
    else:
        return ">200k"


def generate_advisor_predictions(n: int = 2000) -> list[dict]:
    income = rng.lognormal(mean=11.0, sigma=0.8, size=n)
    assets = rng.pareto(3.0, size=n) * 50_000
    risk_tol = rng.uniform(0, 10, size=n)
    age = np.clip(rng.normal(45, 12, size=n), 25, 75)
    time_horizon = rng.integers(1, 30, size=n)
    dti = rng.uniform(0.1, 0.6, size=n)
    goals = rng.integers(0, 5, size=n)
    sex = rng.choice(SEX_VALUES, size=n)
    race = rng.choice(RACE_VALUES, size=n, p=[0.6, 0.13, 0.19, 0.06, 0.02])
    ethnicity = rng.choice(["hispanic", "non-hispanic"], size=n, p=[0.19, 0.81])

    score = (
        0.4 * (income / income.max())
        + 0.3 * (assets / (assets.max() + 1))
        + 0.2 * (risk_tol / 10)
        + 0.1 * (time_horizon / 30)
        - 0.1 * dti
        + rng.normal(0, 0.05, size=n)
    )
    # Inject fairness gap: female group scores ~22% lower → DP ratio ~0.78
    female_mask = sex == "female"
    score[female_mask] *= 0.82

    predictions = []
    base_time = datetime.now(UTC) - timedelta(days=30)
    for i in range(n):
        conf = float(np.clip(abs(score[i] - 0.5) * 2, 0.1, 0.99))
        decision = "matched" if score[i] > 0.5 else "flagged"
        ts = base_time + timedelta(minutes=int(rng.integers(0, 43200)))
        predictions.append({
            "model_id": "model-advisor-v2",
            "model_version": "2.0.0",
            "timestamp": ts,
            "input_features": {
                "income": float(income[i]),
                "investable_assets": float(assets[i]),
                "risk_tolerance_score": float(risk_tol[i]),
                "age": float(age[i]),
                "financial_goals_encoded": int(goals[i]),
                "time_horizon": int(time_horizon[i]),
                "debt_to_income_ratio": float(dti[i]),
            },
            "prediction": float(score[i]),
            "decision": decision,
            "confidence": conf,
            "age_bucket": _age_bucket(age[i]),
            "sex": sex[i],
            "race": race[i],
            "ethnicity": ethnicity[i],
            "income_bracket": _income_bracket(income[i]),
        })
    return predictions


def generate_fraud_predictions(n: int = 1000) -> list[dict]:
    years_exp = rng.integers(1, 40, size=n)
    license_type = rng.integers(0, 4, size=n)
    complaints = rng.integers(0, 10, size=n)
    aum = rng.lognormal(mean=15, sigma=1, size=n)
    firm_size = rng.integers(1, 5, size=n)
    reg_actions = rng.integers(0, 5, size=n)

    risk = (
        -0.3 * (years_exp / 40)
        + 0.4 * (complaints / 10)
        + 0.3 * (reg_actions / 5)
        + rng.uniform(0, 0.1, size=n)
    )
    base_time = datetime.now(UTC) - timedelta(days=30)
    predictions = []
    for i in range(n):
        conf = float(np.clip(abs(risk[i] - 0.5) * 2, 0.1, 0.99))
        decision = "flagged" if risk[i] > 0.5 else "approved"
        ts = base_time + timedelta(minutes=int(rng.integers(0, 43200)))
        predictions.append({
            "model_id": "model-fraud-v1",
            "model_version": "1.0.0",
            "timestamp": ts,
            "input_features": {
                "years_experience": int(years_exp[i]),
                "license_type": int(license_type[i]),
                "complaint_history": int(complaints[i]),
                "assets_under_management": float(aum[i]),
                "firm_size": int(firm_size[i]),
                "regulatory_actions_count": int(reg_actions[i]),
            },
            "prediction": float(risk[i]),
            "decision": decision,
            "confidence": conf,
            "age_bucket": None,
            "sex": None,
            "race": None,
            "ethnicity": None,
            "income_bracket": None,
        })
    return predictions


async def main() -> None:
    print("Generating mock prediction data...")
    advisor_preds = generate_advisor_predictions(2000)
    fraud_preds = generate_fraud_predictions(1000)
    all_preds = advisor_preds + fraud_preds

    async with AsyncSessionLocal() as session:
        batch_size = 500
        for i in range(0, len(all_preds), batch_size):
            batch = all_preds[i : i + batch_size]
            session.add_all([ModelPrediction(**p) for p in batch])
            await session.flush()
            print(f"  Inserted {min(i + batch_size, len(all_preds))}/{len(all_preds)} predictions")
        await session.commit()

    print(f"✓ Inserted {len(all_preds)} mock predictions")
    print(f"  AdvisorMatcher_v2: {len(advisor_preds)} predictions (with ~0.78 DP ratio for female)")
    print(f"  FraudRiskScorer_v1: {len(fraud_preds)} predictions")


if __name__ == "__main__":
    asyncio.run(main())
