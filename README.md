# Sentinel — Continuous AI Audit Platform

Sentinel is a **continuous AI audit and red-teaming platform for financial advisory services**.
It automatically validates, stress-tests, and documents every ML model powering an
advisor-matching platform — replacing a 3–6 month manual audit cycle with a 48-hour automated pipeline.

## Architecture

Four CrewAI agents orchestrated via FastAPI + MySQL + Redis:

| Agent | Responsibility |
|-------|---------------|
| **Auditor** | Hourly fairness monitoring — Demographic Parity, Equalized Odds, Disparate Impact |
| **Red Team** | Adversarial testing — prompt injection (OWASP LLM Top 10) + feature perturbation |
| **Explainer** | SHAP analysis + Spearman stability + LlamaIndex compliance Q&A |
| **Documenter** | Auto-generates SR 11-7 model cards (JSON-LD + Markdown) |

## Stack

- **CrewAI** — multi-agent orchestration
- **LlamaIndex** — RAG over SR 11-7, FCRA, EU AI Act, NIST AI RMF
- **FastAPI** — API layer
- **MySQL** — primary database (audit log: INSERT-only for immutability)
- **Redis** — online compliance feature store
- **MLflow** — model registry + experiment tracking
- **OpenTelemetry** — distributed tracing (Tempo)
- **Prometheus + Grafana** — metrics dashboards
- **Claude (claude-sonnet-4-20250514)** — attacker LLM + judge LLM
- **Next.js + Tailwind** — compliance dashboard

## Quick Start

```bash
# 1. Copy env file and add your Anthropic API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-ant-...

# 2. Start all services
make up

# 3. Install Python dependencies
make install

# 4. Run database migrations and seed demo models
make seed

# 5. Build the LlamaIndex compliance RAG index
make rag-index

# 6. Run the full audit crew
python -m sentinel.agents.crew model-advisor-v2

# 7. Start the API server (separate terminal)
make api

# 8. Start the dashboard (separate terminal)
cd frontend && npm install && npm run dev

# 9. Verify audit chain integrity
make verify-chain

# 10. Run unit tests
make test
```

## Service URLs

| Service | URL |
|---------|-----|
| API docs | http://localhost:8000/docs |
| Grafana | http://localhost:3000 (admin/sentinel) |
| MLflow | http://localhost:5000 |
| Dashboard | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

## Demo Models

| Model | Type | Risk Tier | Notes |
|-------|------|-----------|-------|
| **AdvisorMatcher_v2** | XGBoost classifier | II | Intentional DP gap ~0.78 (female) — fires ACTION alert |
| **FraudRiskScorer_v1** | RandomForest | I | Clean data |
| **HaloAdvisorRAG_v1** | LlamaIndex RAG | III | Primary prompt injection target |

## Guardrails

1. **HITL approval gate** — all ACTION-level alerts require Slack approval before model freeze (24h timeout)
2. **Red team sandbox** — attacks ONLY operate on `/sandbox/*` endpoints (URL allowlist enforced)
3. **Step limit** — max 10 tool calls per agent task
4. **Token budget** — 4,096 output tokens max per task, $5.00 total per crew run
5. **Minimum subgroup size** — fairness alerts only fire when n ≥ 200
6. **Audit log immutability** — MySQL `audit_log` table grants INSERT only (no UPDATE, no DELETE)
7. **Two-tier alerting** — "watch" logs only; "action" requires HITL

## Database Notes

The `audit_log` table is write-once. The application DB user (`sentinel`) has:
- `INSERT` only on `audit_log`
- Full access to all other tables

This is enforced at the DB permission level (see `infra/mysql/init.sql`).

## Regulatory Coverage

- **SR 11-7** — Federal Reserve model risk management
- **FCRA / Regulation B** — Explainability requirements for financial decisions
- **EU AI Act** — Articles 8–15 (high-risk AI requirements)
- **NIST AI RMF 1.0** — Govern / Map / Measure / Manage
- **OWASP LLM Top 10 (2025)** — Adversarial testing framework

## Prometheus Metrics

```
sentinel_audit_duration_seconds         # Histogram, labels: agent, model_id
sentinel_fairness_alert_total           # Counter, labels: alert_level, protected_class
sentinel_red_team_attack_success_rate   # Gauge, labels: model_id, attack_type
sentinel_shap_stability_score          # Gauge, labels: model_id
sentinel_doc_completeness_score        # Gauge, labels: model_id
sentinel_audit_cost_dollars            # Counter, labels: agent, model_id
sentinel_audit_log_chain_valid         # Gauge, 1=intact 0=tampered
sentinel_governance_gate_passed        # Gauge, labels: model_id, gate_name
```

## "Done" Checklist

- [ ] `make up` — all services start
- [ ] `make seed` — demo models and predictions loaded
- [ ] `python scripts/build_rag_index.py` — RAG index built
- [ ] Crew audit fires ACTION alert for AdvisorMatcher_v2 (DP ratio ~0.78)
- [ ] Red team runs prompt injection against HaloAdvisorRAG_v1
- [ ] Explainer returns grounded SR 11-7 citations
- [ ] Documenter generates model card (>90% completeness)
- [ ] Slack HITL approval prompt sent
- [ ] Prometheus metrics at :8001/metrics
- [ ] Grafana dashboard at localhost:3000
- [ ] Dashboard at localhost:3001
- [ ] `make verify-chain` → "chain intact: 100% valid"
- [ ] `make test` → all unit tests pass
- [ ] FastAPI docs at localhost:8000/docs
