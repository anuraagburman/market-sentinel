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
`make dev` waits for Postgres and Redis, then runs API and web as separate processes.
Ctrl-C stops both app process groups. Stop services with `docker compose down`;
Postgres data persists in a named volume.

Compose is for local development: passwordless Postgres trust authentication and
loopback-only service ports. Do not deploy this configuration. The scaffold does
not connect to these services yet; health reports process liveness only.
`.env.example` lists future connection settings with empty values. No environment
file is needed or loaded by the scaffold.

Without Docker, run the apps in separate terminals after `make setup`:

```sh
cd apps/api && uv run --python 3.12 --locked uvicorn app.main:app --reload --host 127.0.0.1
# From the repo root in another terminal:
npm --prefix apps/web run dev
```

## Checks

Run `make setup` first (installation needs registry access). Unit tests require
no Docker or external network; they never call model or data providers.

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
