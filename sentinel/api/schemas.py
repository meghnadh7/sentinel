from __future__ import annotations
"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    risk_tier: str
    validation_status: str
    mlflow_run_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class ModelListResponse(BaseModel):
    models: List[ModelResponse]
    total: int


class FairnessMetricResponse(BaseModel):
    id: int
    protected_class: str
    demographic_parity_ratio: Optional[float]
    equalized_odds_diff: Optional[float]
    disparate_impact_ratio: Optional[float]
    sample_size: Optional[int]
    alert_level: str
    computed_at: datetime
    dp_ratio_ci_lower: Optional[float]
    dp_ratio_ci_upper: Optional[float]


class AlertResponse(BaseModel):
    id: str
    model_id: str
    alert_type: str
    alert_level: str
    message: Optional[str]
    created_at: datetime
    hitl_required: bool
    hitl_approved: Optional[bool]
    hitl_approved_by: Optional[str]
    resolved_at: Optional[datetime]


class AlertApproveRequest(BaseModel):
    approved_by: str = Field(description="Name of approver")


class AuditRequest(BaseModel):
    trigger: str = Field(default="on_demand", description="Trigger reason")
    include_red_team: bool = Field(default=True)
    include_explainability: bool = Field(default=True)
    include_documentation: bool = Field(default=True)


class AuditResponse(BaseModel):
    model_id: str
    audit_id: str
    status: str
    message: str


class RedTeamCampaignRequest(BaseModel):
    model_id: str
    campaign_type: str = Field(default="prompt_injection")
    n_attacks: int = Field(default=20, ge=1, le=10000)


class RedTeamCampaignResponse(BaseModel):
    campaign_id: str
    model_id: str
    status: str
    total_attacks: int
    successful_attacks: int
    attack_success_rate: Optional[float]
    message: str


class GovernanceGateResponse(BaseModel):
    model_id: str
    fairness_gate_passed: Optional[bool]
    robustness_gate_passed: Optional[bool]
    explainability_gate_passed: Optional[bool]
    documentation_gate_passed: Optional[bool]
    all_gates_passed: Optional[bool]
    promotion_blocked: bool


class ModelCardResponse(BaseModel):
    id: str
    model_id: str
    version: int
    completeness_score: Optional[float]
    generated_at: datetime
    approved_by: Optional[str]
    content_json: Dict[str, Any]


class ComplianceStatusResponse(BaseModel):
    model_id: str
    model_name: str
    risk_tier: str
    validation_status: str
    fairness_alert_count: int
    open_action_alerts: int
    latest_completeness_score: Optional[float]
    governance_gate_status: Optional[GovernanceGateResponse]
