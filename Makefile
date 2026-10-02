UV ?= uv
export UV_PYTHON := 3.12
export NEXT_TELEMETRY_DISABLED := 1
DEV_DATABASE_URL ?= postgresql+psycopg://sentinel@localhost:5432/sentinel

.PHONY: setup dev seed-dev test lint contracts eval-smoke test-e2e
setup:
	$(UV) sync --project apps/api --locked
	npm --prefix apps/web ci

dev: setup
	docker compose up -d --wait
	cd apps/api && DATABASE_URL=$(DEV_DATABASE_URL) $(UV) run --locked alembic upgrade head
	DATABASE_URL=$(DEV_DATABASE_URL) $(UV) run --project apps/api --no-sync python apps/api/dev.py

seed-dev:
	cd apps/api && MS_ENV=dev DATABASE_URL=$(DEV_DATABASE_URL) $(UV) run --locked python -m app.db.seed_fixture

test:
	$(UV) run --project apps/api --locked pytest apps/api/tests packages/contracts/tests evals/tests
	npm --prefix apps/web test

lint:
	$(UV) run --project apps/api --locked ruff check apps/api workers
	$(UV) run --project apps/api --locked ruff format --check apps/api workers
	npm --prefix apps/web run lint

contracts:
	cd apps/api && $(UV) run --locked python -m app.export_openapi

eval-smoke:
	@echo "no suites yet"

test-e2e:
	npm --prefix apps/web run test:e2e
