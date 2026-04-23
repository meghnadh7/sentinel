# Sentinel

A continuous audit and red-teaming system for ML models in financial advisory. The idea came from watching teams spend months manually reviewing models before they could go to production — this compresses that down to ~48 hours.

It runs four agents (fairness auditor, red teamer, explainer, documenter) that work through a model end-to-end and flag anything that needs human review before promotion.

## What it does

- Checks models for demographic bias across protected classes (sex, race, age, income bracket) using fairlearn, with bootstrap confidence intervals so you know how much to trust the numbers
- Runs prompt injection and feature perturbation attacks mapped to OWASP LLM Top 10
- Generates SHAP explanations and monitors whether feature importance shifts over time
- Writes model cards that satisfy SR 11-7, FCRA/Reg B, and EU AI Act requirements
- Keeps an append-only hash-chained audit log so you can prove nothing was tampered with
- Blocks model promotion if any governance gate fails, with a Slack-based approval workflow for the human-in-the-loop step

## Stack



- **CrewAI** for agent orchestration
- **LlamaIndex** for RAG over the regulatory documents (SR 11-7, FCRA, Reg B, EU AI Act, NIST AI RMF)
- **FastAPI** + **MySQL** + **Redis**
- **MLflow** for model registry
- **OpenTelemetry** → Tempo for traces, **Prometheus** → Grafana for metrics
- **Claude** (claude-sonnet-4-20250514) as the attacker and judge in red team runs
- **Next.js + Tailwind** for the compliance dashboard

## Running it

You need Docker and Python 3.9+.

```bash
cp .env.example .env
# add ANTHROPIC_API_KEY to .env

make up        # starts MySQL, Redis, MLflow, Prometheus, Grafana
make install   # pip install
make seed      # loads demo models + 2000 synthetic predictions
make rag-index # builds the LlamaIndex compliance index

# run the audit crew against a model
python -m sentinel.agents.crew model-advisor-v2

# in separate terminals:
make api       # FastAPI on :8000
cd frontend && npm install && npm run dev  # dashboard on :3001
```

No API key? Run with `USE_MOCK_LLM=true` in your `.env` — everything works except the actual LLM calls get stubbed out.

## URLs

| | |
|---|---|
| API docs | http://localhost:8000/docs |
| Dashboard | http://localhost:3001 |
| Grafana | http://localhost:3000 — admin/sentinel |
| MLflow | http://localhost:5000 |
| Prometheus | http://localhost:9090 |

## Demo models

Three models come pre-seeded:

- **AdvisorMatcher_v2** — has an intentional fairness gap (DP ratio ~0.78 for female group). This is the one that fires the action alert and triggers HITL approval.
- **FraudRiskScorer_v1** — clean, used to show a passing audit
- **HaloAdvisorRAG_v1** — the RAG agent, primary target for prompt injection testing

## Guardrails

A few things worth knowing before you run this:

1. Red team attacks only hit `/sandbox/*` endpoints — the URL allowlist is enforced in code, not just config
2. Each agent is capped at 10 tool calls, 4096 output tokens, and $5 per crew run
3. Fairness alerts only fire when a subgroup has at least 200 samples — smaller than that and the numbers aren't reliable
4. The audit log table has INSERT-only DB permissions. You literally cannot UPDATE or DELETE a row, even if you have the password.
5. ACTION-level alerts require a named human to approve in Slack before anything gets unblocked. Watch-level alerts just log.

## Regulatory coverage

SR 11-7, FCRA, Regulation B, EU AI Act (Articles 8–15), NIST AI RMF 1.0, OWASP LLM Top 10 (2025).

## Tests

```bash
make test   # 26 unit tests
```

Integration tests require a running MySQL and Redis — they're wired into the GitHub Actions CI workflow.
