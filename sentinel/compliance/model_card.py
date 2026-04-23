from __future__ import annotations
"""Model card generation (JSON-LD + Markdown)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sentinel.compliance.sr11_7 import (
    NIST_AI_RMF_FUNCTIONS,
    REQUIRED_DOCUMENTATION_SECTIONS,
    RISK_TIER_DESCRIPTIONS,
)
from sentinel.config import get_settings

settings = get_settings()
UTC = timezone.utc


def compute_completeness_score(card_json: Dict[str, Any]) -> float:
    present = sum(
        1 for s in REQUIRED_DOCUMENTATION_SECTIONS
        if s in card_json and card_json[s] not in (None, "", {}, [])
    )
    return present / len(REQUIRED_DOCUMENTATION_SECTIONS)


async def generate_model_card(
    model_id: str,
    fairness_summary: Optional[Dict[str, Any]] = None,
    red_team_summary: Optional[Dict[str, Any]] = None,
    explainability_summary: Optional[Dict[str, Any]] = None,
    regulatory_evidence: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    from sentinel.data.database import AsyncSessionLocal
    from sentinel.data.models import Model
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Model).where(Model.id == model_id))
        model = result.scalar_one_or_none()

    model_name = model.name if model else model_id
    risk_tier = model.risk_tier if model else "II"
    model_version = model.version if model else "unknown"

    content_json: Dict[str, Any] = {
        "@context": "https://schema.org/",
        "@type": "MLModel",
        "model_purpose": (
            f"{model_name} is a machine learning model used for financial advisor matching "
            f"and risk assessment in the Datalign Advisory platform."
        ),
        "risk_tier": risk_tier,
        "risk_tier_description": RISK_TIER_DESCRIPTIONS.get(risk_tier, "Unknown"),
        "model_version": model_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "training_data_provenance": {
            "description": "Consumer financial profile data with demographic attributes",
            "features": ["income", "investable_assets", "risk_tolerance_score", "age",
                        "financial_goals_encoded", "time_horizon", "debt_to_income_ratio"],
            "protected_classes_logged": ["age_bucket", "sex", "race", "ethnicity", "income_bracket"],
            "data_governance": "Internal data with PII handling per CCPA requirements",
        },
        "fairness_metrics_summary": fairness_summary or {},
        "red_team_results_summary": red_team_summary or {},
        "explainability_summary": explainability_summary or {},
        "approval_chain": {
            "model_owner": "Data Science Team",
            "validation_owner": "Model Risk Management",
            "business_owner": "Financial Services Product",
            "approval_required_before_production": True,
        },
        "nist_ai_rmf_mapping": NIST_AI_RMF_FUNCTIONS,
        "regulatory_citations": regulatory_evidence or {
            "SR_11-7": "Section 4 — Model documentation, validation, and governance requirements",
            "FCRA": "Section 615 — Adverse action notification requirements",
            "Regulation_B": "Section 202.9 — Notice requirements for adverse actions",
            "EU_AI_Act": "Articles 11-13 — Technical documentation and transparency",
        },
        "known_limitations": [
            "Model performance may degrade on consumer profiles outside training distribution",
            "Fairness metrics computed on sampled data with 95% bootstrap CI",
            "Protected class labels are self-reported and may contain noise",
        ],
    }

    completeness_score = compute_completeness_score(content_json)
    content_markdown = render_markdown(content_json)

    return {
        "id": str(uuid.uuid4()),
        "model_id": model_id,
        "content_json": content_json,
        "content_markdown": content_markdown,
        "completeness_score": completeness_score,
    }


def render_markdown(content_json: Dict[str, Any]) -> str:
    lines = [
        f"# Model Card: {content_json.get('model_purpose', 'Unknown Model')[:80]}",
        f"\n**Generated:** {content_json.get('generated_at', 'N/A')}",
        f"**Risk Tier:** {content_json.get('risk_tier', 'N/A')} — "
        f"{content_json.get('risk_tier_description', '')}",
        f"**Version:** {content_json.get('model_version', 'N/A')}",
        "\n---\n",
        "## Training Data Provenance",
    ]

    provenance = content_json.get("training_data_provenance", {})
    if provenance:
        lines.append(f"\n{provenance.get('description', '')}")
        if "features" in provenance:
            lines.append("\n**Features:** " + ", ".join(provenance["features"]))
        if "protected_classes_logged" in provenance:
            lines.append("**Protected classes:** " + ", ".join(provenance["protected_classes_logged"]))

    lines.append("\n## Fairness Metrics Summary\n")
    fairness = content_json.get("fairness_metrics_summary", {})
    if fairness:
        lines.append(f"```json\n{str(fairness)[:800]}\n```")
    else:
        lines.append("_Not yet computed_")

    lines.append("\n## Red Team Results Summary\n")
    red_team = content_json.get("red_team_results_summary", {})
    if red_team:
        lines.append(f"```json\n{str(red_team)[:800]}\n```")
    else:
        lines.append("_Not yet computed_")

    lines.append("\n## Explainability Summary\n")
    explain = content_json.get("explainability_summary", {})
    if explain:
        lines.append(f"```json\n{str(explain)[:800]}\n```")
    else:
        lines.append("_Not yet computed_")

    lines.append("\n## NIST AI RMF Mapping\n")
    nist = content_json.get("nist_ai_rmf_mapping", {})
    for func_name, items in nist.items():
        lines.append(f"\n### {func_name}")
        for item in items:
            lines.append(f"- {item}")

    lines.append("\n## Regulatory Citations\n")
    citations = content_json.get("regulatory_citations", {})
    for reg, citation in citations.items():
        lines.append(f"- **{reg}:** {citation}")

    lines.append("\n## Known Limitations\n")
    for limitation in content_json.get("known_limitations", []):
        lines.append(f"- {limitation}")

    lines.append("\n## Approval Chain\n")
    approval = content_json.get("approval_chain", {})
    for k, v in approval.items():
        lines.append(f"- **{k}:** {v}")

    return "\n".join(lines)
