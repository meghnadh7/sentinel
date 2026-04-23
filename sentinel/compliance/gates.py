from __future__ import annotations
"""CI/CD governance gate logic."""

from dataclasses import dataclass, field
from typing import Any

from sentinel.config import get_settings

settings = get_settings()


@dataclass
class GateResult:
    fairness_gate_passed: bool
    robustness_gate_passed: bool
    explainability_gate_passed: bool
    documentation_gate_passed: bool
    all_passed: bool
    promotion_blocked: bool
    failed_gates: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fairness_gate_passed": self.fairness_gate_passed,
            "robustness_gate_passed": self.robustness_gate_passed,
            "explainability_gate_passed": self.explainability_gate_passed,
            "documentation_gate_passed": self.documentation_gate_passed,
            "all_gates_passed": self.all_passed,
            "promotion_blocked": self.promotion_blocked,
            "failed_gates": self.failed_gates,
            "details": self.details,
        }


class GovernanceGateChecker:
    def check_all(
        self,
        fairness_ok: bool,
        robustness_ok: bool,
        explainability_ok: bool,
        documentation_ok: bool,
        details: dict[str, Any] | None = None,
    ) -> GateResult:
        failed = []
        if not fairness_ok:
            failed.append("fairness")
        if not robustness_ok:
            failed.append("robustness")
        if not explainability_ok:
            failed.append("explainability")
        if not documentation_ok:
            failed.append("documentation")

        all_passed = len(failed) == 0
        return GateResult(
            fairness_gate_passed=fairness_ok,
            robustness_gate_passed=robustness_ok,
            explainability_gate_passed=explainability_ok,
            documentation_gate_passed=documentation_ok,
            all_passed=all_passed,
            promotion_blocked=not all_passed,
            failed_gates=failed,
            details=details or {},
        )

    async def evaluate_model(self, model_id: str) -> GateResult:
        from sentinel.data.database import AsyncSessionLocal
        from sentinel.data.models import FairnessMetric, ModelCard, RedTeamCampaign, ShapAnalysis
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            # Fairness gate: latest metrics all pass threshold
            fairness_result = await session.execute(
                select(FairnessMetric)
                .where(FairnessMetric.model_id == model_id)
                .order_by(FairnessMetric.computed_at.desc())
                .limit(10)
            )
            metrics = fairness_result.scalars().all()
            fairness_ok = all(
                m.alert_level == "none" for m in metrics
            ) if metrics else False

            # Robustness gate: latest campaign success rate < threshold
            rt_result = await session.execute(
                select(RedTeamCampaign)
                .where(RedTeamCampaign.model_id == model_id)
                .where(RedTeamCampaign.status == "completed")
                .order_by(RedTeamCampaign.completed_at.desc())
                .limit(1)
            )
            campaign = rt_result.scalar_one_or_none()
            robustness_ok = (
                campaign.attack_success_rate <= settings.red_team_success_rate_threshold
                if campaign else False
            )

            # Explainability gate: latest SHAP no stability alert
            shap_result = await session.execute(
                select(ShapAnalysis)
                .where(ShapAnalysis.model_id == model_id)
                .order_by(ShapAnalysis.analyzed_at.desc())
                .limit(1)
            )
            shap = shap_result.scalar_one_or_none()
            explainability_ok = (not shap.stability_alert) if shap else False

            # Documentation gate: latest model card completeness >= threshold
            card_result = await session.execute(
                select(ModelCard)
                .where(ModelCard.model_id == model_id)
                .order_by(ModelCard.version.desc())
                .limit(1)
            )
            card = card_result.scalar_one_or_none()
            documentation_ok = (
                card.completeness_score >= settings.doc_completeness_threshold
                if card else False
            )

        return self.check_all(
            fairness_ok=fairness_ok,
            robustness_ok=robustness_ok,
            explainability_ok=explainability_ok,
            documentation_ok=documentation_ok,
            details={
                "fairness_metrics_count": len(metrics),
                "latest_attack_success_rate": campaign.attack_success_rate if campaign else None,
                "shap_stability_alert": shap.stability_alert if shap else None,
                "doc_completeness_score": card.completeness_score if card else None,
            },
        )
