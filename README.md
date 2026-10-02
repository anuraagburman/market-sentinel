# Market Sentinel

Evidence-first equity research. Research and paper decisions only; no live orders.

## Setup

Prerequisites: Node.js 24.14.0 (npm 11), uv 0.10.9, and Docker Compose v2 for the
full stack. uv provisions Python 3.12. Dependencies use exact pins and lockfiles.

```sh
make setup
make dev
```

Open http://127.0.0.1:3000, http://127.0.0.1:8000/health, or http://127.0.0.1:8000/docs.
`make dev` waits for Postgres and Redis, upgrades the database to Alembic head, then runs API and web.
Override `DEV_DATABASE_URL` to use a different dev database.
Ctrl-C stops both app process groups. Stop services with `docker compose down`;
Postgres data persists in a named volume.

Compose is for local development: passwordless Postgres trust authentication and
loopback-only service ports. Do not deploy this configuration. The API uses Postgres when `DATABASE_URL` is set, and fails startup if the database is
unreachable or below Alembic head. Without it, previews and portfolios use memory;
startup logs this once. Health reports process liveness only. Environment files are
not loaded automatically.

Fresh databases are empty. `make seed-dev` explicitly inserts the synthetic fixture
once. The module command `MS_ENV=dev DATABASE_URL=… uv run python -m app.db.seed_fixture`
(from `apps/api`) also works; it refuses environments other than `dev` or `test`.

Without Docker, run the apps in separate terminals after `make setup`:

```sh
cd apps/api && uv run --python 3.12 --locked uvicorn app.main:app --reload --host 127.0.0.1
# From the repo root in another terminal:
npm --prefix apps/web run dev
```

## Checks

Run `make setup` first (installation needs registry access). Memory unit tests require no Docker. Postgres integration tests use a local test
database and real commits; they never call model or data providers. Without
`TEST_DATABASE_URL`, integration tests visibly skip. CI requires the URL and runs
Postgres 17.4; it cannot pass by skipping these tests.

```sh
docker compose up -d --wait postgres
TEST_DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test make test
cd apps/api && DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test uv run alembic check
```

The test harness creates the database if missing and truncates application tables
before each test. It refuses any database whose name does not end in `_test`.

```sh
make test          # pytest + Vitest
make lint          # Ruff, ESLint, TypeScript
make contracts     # regenerate packages/contracts/openapi.json
make eval-smoke    # stub: no suites yet
cd apps/web && npx playwright install chromium  # one-time browser download
cd ../..
make test-e2e      # local Next.js server + Chromium smoke
```

CI runs lint, unit tests, contract freshness, production build, and browser smoke
on pushes and pull requests. Commit generated OpenAPI changes with API changes.

Start here: `docs/handoffs/CURRENT.md`, `docs/tasks/LEDGER.md`, and `AGENTS.md`.
