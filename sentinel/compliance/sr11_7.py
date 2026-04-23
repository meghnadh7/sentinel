from __future__ import annotations
"""SR 11-7 compliance mapping constants."""

RISK_TIER_DESCRIPTIONS = {
    "I": "Low risk — internal operational models, limited financial impact",
    "II": "Moderate risk — consumer-facing matching and recommendation models",
    "III": "High risk — agentic AI systems, autonomous decision-making",
    "IV": "Critical risk — systemic risk models, capital calculation models",
}

VALIDATION_FREQUENCY = {
    "I": "semi-annually",
    "II": "quarterly",
    "III": "monthly",
    "IV": "monthly",
}

REQUIRED_DOCUMENTATION_SECTIONS = [
    "model_purpose",
    "risk_tier",
    "training_data_provenance",
    "fairness_metrics_summary",
    "red_team_results_summary",
    "explainability_summary",
    "approval_chain",
    "nist_ai_rmf_mapping",
    "regulatory_citations",
    "known_limitations",
]

NIST_AI_RMF_FUNCTIONS = {
    "GOVERN": [
        "GOVERN 1.1: Organizational policies address AI risks",
        "GOVERN 2.1: Roles and responsibilities documented",
        "GOVERN 6.1: Policies for AI deployment risks",
        "GOVERN 6.2: Contingency processes for AI failures",
    ],
    "MAP": [
        "MAP 1.1: Context established for AI risk assessment",
        "MAP 1.5: Organizational risk tolerance documented",
        "MAP 2.3: Third-party risks mapped",
        "MAP 3.3: Bias and fairness risks mapped",
        "MAP 3.4: Explainability risks mapped",
    ],
    "MEASURE": [
        "MEASURE 1.1: Measurement approaches identified",
        "MEASURE 2.3: Performance criteria measured and documented",
        "MEASURE 2.7: Adversarial testing evaluated and documented",
        "MEASURE 2.11: Fairness and bias evaluated",
    ],
    "MANAGE": [
        "MANAGE 1.1: AI system achieves intended purpose without harm",
        "MANAGE 2.2: Mechanisms to neutralize harms",
        "MANAGE 3.1: Risks and benefits documented",
        "MANAGE 4.2: Incident response procedures",
    ],
}

OWASP_LLM_TOP_10_2025 = {
    "LLM01": "Prompt Injection",
    "LLM02": "Sensitive Information Disclosure",
    "LLM03": "Supply Chain",
    "LLM04": "Data and Model Poisoning",
    "LLM05": "Improper Output Handling",
    "LLM06": "Excessive Agency",
    "LLM07": "System Prompt Leakage",
    "LLM08": "Vector and Embedding Weaknesses",
    "LLM09": "Misinformation",
    "LLM10": "Unbounded Consumption",
}
