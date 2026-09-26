# Handoff — T-001 Repo skeleton, Makefile, CI

- **Updated:** 2026-09-26 by Codex
- **Branch / worktree:** task/T-001-skeleton @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews T-001; with Docker running, run `make dev` and confirm Postgres
and Redis become healthy alongside the API and web.

## Done this session
- Added FastAPI/Pydantic health endpoint and in-process tests; installed SQLAlchemy,
  Alembic, and psycopg with exact dependency pins and a uv lockfile.
- Added Next.js/React/TypeScript/Tailwind placeholder, Vitest coverage, and Playwright smoke.
- Added local Postgres/Redis Compose services, a process-group-aware app launcher,
  Makefile targets, and CI for lint, tests, contract freshness, build, and browser smoke.
- Exported health-only OpenAPI in packages/contracts/openapi.json; no T-002 schemas edited.
- Updated README and AGENTS.md commands; documented Docker-free app startup.

## Tests run
- `make lint` → pass (Ruff, ESLint, Next route types, TypeScript).
- `make test` → pass (2 pytest tests + 1 Vitest test).
- `make contracts && git diff --exit-code packages/contracts` → pass after staging generated contract.
- `make eval-smoke` → pass, prints "no suites yet".
- `npm --prefix apps/web run build` → pass.
- `make test-e2e` equivalent (`npm run test:e2e` in apps/web) → pass (1 Chromium smoke).
- `npm ci` → pass; npm audit reported 0 vulnerabilities after patched Vitest pin.
- `docker compose config --quiet` → pass.
- Temporary local integration check → API health and web page respond; SIGTERM shuts
  down both process groups and releases ports 8000/3000.
- `git diff --check` → pass.

## Contract changes proposed (not applied)
- none; generated health-only OpenAPI is included under T-001 ownership.

## Unresolved / assumptions
- Docker is installed but its daemon is stopped. Full `make dev` service startup remains
  unverified; app-process startup/shutdown was verified independently.
- Compose is local-only, with passwordless Postgres trust and loopback-bound ports.
  Health is process liveness, not dependency readiness. No database connections yet.
- One upstream Starlette/AnyIO deprecation warning appears in pytest; tests pass.
- uv 0.10.9 was installed in a temporary tool environment for validation. Commands used
  `UV=/private/tmp/t001-tools/bin/uv`; users should install uv as documented in README.
- Remote GitHub Actions execution awaits push; nothing was pushed.
