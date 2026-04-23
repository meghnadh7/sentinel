.PHONY: up down test seed demo build logs shell clean install

up:
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "Services started. API: http://localhost:8000 | Grafana: http://localhost:3000 | MLflow: http://localhost:5000"

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

install:
	pip install -e ".[dev]"

migrate:
	python -c "import asyncio; from sentinel.data.database import create_tables; asyncio.run(create_tables())"

seed: migrate
	python scripts/seed_demo_models.py
	python scripts/generate_mock_predictions.py

rag-index:
	python scripts/build_rag_index.py

demo: seed rag-index
	@echo "Demo data loaded. Starting audit crew..."
	python -m sentinel.agents.crew

verify-chain:
	python scripts/verify_audit_chain.py

test:
	pytest tests/unit/ -v --tb=short

test-all:
	pytest tests/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

api:
	uvicorn sentinel.api.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

shell:
	docker compose exec api bash

fmt:
	ruff format sentinel/ tests/ scripts/
	ruff check --fix sentinel/ tests/ scripts/

lint:
	ruff check sentinel/ tests/ scripts/
	mypy sentinel/
