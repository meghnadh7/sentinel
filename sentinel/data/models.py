from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinel.data.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_tier: Mapped[str] = mapped_column(Enum("I", "II", "III", "IV"), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        Enum("pending", "validated", "expired", "flagged"), default="pending"
    )
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    predictions: Mapped[List["ModelPrediction"]] = relationship(back_populates="model")
    fairness_metrics: Mapped[List["FairnessMetric"]] = relationship(back_populates="model")
    red_team_campaigns: Mapped[List["RedTeamCampaign"]] = relationship(back_populates="model")
    shap_analyses: Mapped[List["ShapAnalysis"]] = relationship(back_populates="model")
    model_cards: Mapped[List["ModelCard"]] = relationship(back_populates="model")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="model")
    governance_gates: Mapped[List["GovernanceGate"]] = relationship(back_populates="model")


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    input_features: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    prediction: Mapped[Optional[float]] = mapped_column(Float)
    decision: Mapped[Optional[str]] = mapped_column(
        Enum("approved", "denied", "matched", "flagged")
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    age_bucket: Mapped[Optional[str]] = mapped_column(String(20))
    sex: Mapped[Optional[str]] = mapped_column(String(20))
    race: Mapped[Optional[str]] = mapped_column(String(50))
    ethnicity: Mapped[Optional[str]] = mapped_column(String(50))
    income_bracket: Mapped[Optional[str]] = mapped_column(String(20))

    model: Mapped["Model"] = relationship(back_populates="predictions")


class FairnessMetric(Base):
    __tablename__ = "fairness_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    protected_class: Mapped[str] = mapped_column(String(50), nullable=False)
    demographic_parity_ratio: Mapped[Optional[float]] = mapped_column(Float)
    equalized_odds_diff: Mapped[Optional[float]] = mapped_column(Float)
    disparate_impact_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer)
    alert_level: Mapped[str] = mapped_column(
        Enum("none", "watch", "action"), default="none"
    )
    dp_ratio_ci_lower: Mapped[Optional[float]] = mapped_column(Float)
    dp_ratio_ci_upper: Mapped[Optional[float]] = mapped_column(Float)

    model: Mapped["Model"] = relationship(back_populates="fairness_metrics")


class RedTeamCampaign(Base):
    __tablename__ = "red_team_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    campaign_type: Mapped[str] = mapped_column(
        Enum("prompt_injection", "feature_perturbation"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    total_attacks: Mapped[int] = mapped_column(Integer, default=0)
    successful_attacks: Mapped[int] = mapped_column(Integer, default=0)
    attack_success_rate: Mapped[Optional[float]] = mapped_column(Float)
    llm_cost_dollars: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        Enum("running", "completed", "failed", "budget_exceeded"), default="running"
    )

    model: Mapped["Model"] = relationship(back_populates="red_team_campaigns")
    attacks: Mapped[List["RedTeamAttack"]] = relationship(back_populates="campaign")


class RedTeamAttack(Base):
    __tablename__ = "red_team_attacks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("red_team_campaigns.id"), nullable=False
    )
    attack_type: Mapped[Optional[str]] = mapped_column(String(100))
    owasp_category: Mapped[Optional[str]] = mapped_column(String(100))
    attack_input: Mapped[Optional[str]] = mapped_column(Text)
    model_response: Mapped[Optional[str]] = mapped_column(Text)
    attack_succeeded: Mapped[Optional[bool]] = mapped_column(Boolean)
    judge_reasoning: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    campaign: Mapped["RedTeamCampaign"] = relationship(back_populates="attacks")


class ShapAnalysis(Base):
    __tablename__ = "shap_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    feature_importance: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    spearman_rho: Mapped[Optional[float]] = mapped_column(Float)
    baseline_rho_at_validation: Mapped[Optional[float]] = mapped_column(Float)
    stability_alert: Mapped[bool] = mapped_column(Boolean, default=False)

    model: Mapped["Model"] = relationship(back_populates="shap_analyses")


class ModelCard(Base):
    __tablename__ = "model_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_markdown: Mapped[Optional[str]] = mapped_column(Text)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float)
    generated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    approved_by: Mapped[Optional[str]] = mapped_column(String(255))
    approved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    model: Mapped["Model"] = relationship(back_populates="model_cards")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(
        Enum("fairness", "robustness", "stability", "documentation", "audit_chain"),
        nullable=False,
    )
    alert_level: Mapped[str] = mapped_column(Enum("watch", "action"), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    hitl_required: Mapped[bool] = mapped_column(Boolean, default=False)
    hitl_approved: Mapped[Optional[bool]] = mapped_column(Boolean)
    hitl_approved_by: Mapped[Optional[str]] = mapped_column(String(255))
    hitl_approved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    model: Mapped["Model"] = relationship(back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[Optional[str]] = mapped_column(String(36))
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class GovernanceGate(Base):
    __tablename__ = "governance_gates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    fairness_gate_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    robustness_gate_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    explainability_gate_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    documentation_gate_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    all_gates_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    promotion_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    model: Mapped["Model"] = relationship(back_populates="governance_gates")
