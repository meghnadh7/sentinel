from __future__ import annotations
#!/usr/bin/env python3
"""Register the three demo models in MLflow and MySQL."""

import asyncio
import sys
import uuid

import mlflow
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

sys.path.insert(0, ".")

from sentinel.config import get_settings
from sentinel.data.database import AsyncSessionLocal, create_tables
from sentinel.data.models import Model

settings = get_settings()
mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

rng = np.random.default_rng(42)


def _train_advisor_matcher() -> GradientBoostingClassifier:
    """Train AdvisorMatcher_v2 with intentional fairness gap."""
    n = 5000
    income = rng.lognormal(mean=11.0, sigma=0.8, size=n)
    assets = rng.pareto(3.0, size=n) * 50_000
    risk_tol = rng.uniform(0, 10, size=n)
    age = rng.integers(25, 75, size=n)
    time_horizon = rng.integers(1, 30, size=n)
    dti = rng.uniform(0.1, 0.6, size=n)
    goals = rng.integers(0, 5, size=n)
    sex = rng.choice([0, 1], size=n)

    score = (
        0.4 * (income / income.max())
        + 0.3 * (assets / (assets.max() + 1))
        + 0.2 * (risk_tol / 10)
        + 0.1 * (time_horizon / 30)
        - 0.1 * dti
        + rng.normal(0, 0.05, size=n)
    )
    score[sex == 0] *= 0.82

    labels = np.where(score > 0.6, 2, np.where(score > 0.3, 1, 0))
    X = np.column_stack([income, assets, risk_tol, age, goals, time_horizon, dti])

    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model.fit(X, labels)
    return model


def _train_fraud_risk_scorer() -> RandomForestClassifier:
    """Train FraudRiskScorer_v1."""
    n = 3000
    years_exp = rng.integers(1, 40, size=n)
    license_type = rng.integers(0, 4, size=n)
    complaints = rng.integers(0, 10, size=n)
    aum = rng.lognormal(mean=15, sigma=1, size=n)
    firm_size = rng.integers(1, 5, size=n)
    reg_actions = rng.integers(0, 5, size=n)

    risk_score = (
        -0.3 * (years_exp / 40)
        + 0.4 * (complaints / 10)
        + 0.3 * (reg_actions / 5)
        + rng.uniform(0, 0.1, size=n)
    )
    labels = np.where(risk_score > 0.5, 2, np.where(risk_score > 0.2, 1, 0))
    X = np.column_stack([years_exp, license_type, complaints, aum, firm_size, reg_actions])

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, labels)
    return model


async def seed_mysql_models(runs: dict[str, str]) -> None:
    await create_tables()
    async with AsyncSessionLocal() as session:
        models = [
            Model(
                id="model-advisor-v2",
                name="AdvisorMatcher_v2",
                version="2.0.0",
                risk_tier="II",
                validation_status="validated",
                mlflow_run_id=runs["advisor"],
            ),
            Model(
                id="model-fraud-v1",
                name="FraudRiskScorer_v1",
                version="1.0.0",
                risk_tier="I",
                validation_status="validated",
                mlflow_run_id=runs["fraud"],
            ),
            Model(
                id="model-halo-rag-v1",
                name="HaloAdvisorRAG_v1",
                version="1.0.0",
                risk_tier="III",
                validation_status="pending",
                mlflow_run_id=None,
            ),
        ]
        for m in models:
            existing = await session.get(Model, m.id)
            if not existing:
                session.add(m)
        await session.commit()
    print("✓ MySQL models registered")


async def main() -> None:
    print("Seeding demo models...")
    print("  Training AdvisorMatcher_v2 (GradientBoosting)...")
    _train_advisor_matcher()
    print("  ✓ AdvisorMatcher_v2 trained")

    print("  Training FraudRiskScorer_v1 (RandomForest)...")
    _train_fraud_risk_scorer()
    print("  ✓ FraudRiskScorer_v1 trained")

    await seed_mysql_models({"advisor": "demo-run-advisor", "fraud": "demo-run-fraud"})
    print("✓ All demo models seeded successfully")


if __name__ == "__main__":
    asyncio.run(main())
