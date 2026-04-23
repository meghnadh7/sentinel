from __future__ import annotations
"""Prometheus metrics for Sentinel."""

import threading

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from sentinel.config import get_settings

settings = get_settings()

# Audit duration
audit_duration = Histogram(
    "sentinel_audit_duration_seconds",
    "Duration of audit pipeline runs",
    labelnames=["agent", "model_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# Fairness alerts
fairness_alert_total = Counter(
    "sentinel_fairness_alert_total",
    "Total fairness alerts fired",
    labelnames=["alert_level", "protected_class"],
)

# Red team attack success rate
red_team_attack_success_rate = Gauge(
    "sentinel_red_team_attack_success_rate",
    "Latest attack success rate per model and attack type",
    labelnames=["model_id", "attack_type"],
)

# SHAP stability score
shap_stability_score = Gauge(
    "sentinel_shap_stability_score",
    "Latest Spearman rho for SHAP feature importance stability",
    labelnames=["model_id"],
)

# Documentation completeness
doc_completeness_score = Gauge(
    "sentinel_doc_completeness_score",
    "Latest model card completeness score",
    labelnames=["model_id"],
)

# LLM cost
audit_cost_dollars = Counter(
    "sentinel_audit_cost_dollars",
    "Total LLM cost in dollars",
    labelnames=["agent", "model_id"],
)

# Audit log chain validity
audit_log_chain_valid = Gauge(
    "sentinel_audit_log_chain_valid",
    "1 if audit log hash chain is intact, 0 if tampered",
)
audit_log_chain_valid.set(1)

# Governance gates
governance_gate_passed = Gauge(
    "sentinel_governance_gate_passed",
    "Whether a governance gate passed for a model",
    labelnames=["model_id", "gate_name"],
)


def setup_prometheus() -> None:
    def _start():
        try:
            start_http_server(settings.prometheus_port)
        except Exception as e:
            print(f"[Prometheus] Failed to start metrics server: {e}")

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()


def record_fairness_alert(alert_level: str, protected_class: str) -> None:
    fairness_alert_total.labels(
        alert_level=alert_level, protected_class=protected_class
    ).inc()


def record_audit_duration(agent: str, model_id: str, duration_seconds: float) -> None:
    audit_duration.labels(agent=agent, model_id=model_id).observe(duration_seconds)


def record_red_team_result(model_id: str, attack_type: str, success_rate: float) -> None:
    red_team_attack_success_rate.labels(
        model_id=model_id, attack_type=attack_type
    ).set(success_rate)


def record_shap_stability(model_id: str, rho: float) -> None:
    shap_stability_score.labels(model_id=model_id).set(rho)


def record_doc_completeness(model_id: str, score: float) -> None:
    doc_completeness_score.labels(model_id=model_id).set(score)


def record_audit_cost(agent: str, model_id: str, cost_dollars: float) -> None:
    audit_cost_dollars.labels(agent=agent, model_id=model_id).inc(cost_dollars)


def record_gate_result(model_id: str, gate_name: str, passed: bool) -> None:
    governance_gate_passed.labels(model_id=model_id, gate_name=gate_name).set(1 if passed else 0)


def set_chain_validity(is_valid: bool) -> None:
    audit_log_chain_valid.set(1 if is_valid else 0)
