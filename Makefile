UV ?= uv
export UV_PYTHON := 3.12
export NEXT_TELEMETRY_DISABLED := 1

.PHONY: setup dev test lint contracts eval-smoke test-e2e
setup:
	$(UV) sync --project apps/api --locked
	npm --prefix apps/web ci

dev: setup
	docker compose up -d --wait
	$(UV) run --project apps/api --no-sync python apps/api/dev.py

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
