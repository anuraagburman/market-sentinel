# T-001 — Repo skeleton, Makefile, CI

- **Implementer:** Codex   **Reviewer:** Claude Code
- **Branch:** task/T-001-skeleton   **Depends on:** —   **Effort:** default

## Problem
No runnable project exists. Both lanes need a skeleton with working test commands before any
feature work, and CI that runs them.

## User-visible outcome
`make dev` starts Postgres + Redis + a FastAPI health endpoint + a Next.js page; `make test` runs
pytest and Vitest and passes; CI runs `make test` on every push.

## Read (only these)
- `docs/architecture.md` — "Stack" and "Repository structure"
- `AGENTS.md`

## Owned paths
`apps/web/` (scaffold only), `apps/api/` (scaffold only), `workers/` (empty package),
`packages/`, `compose.yaml`, `Makefile`, `.github/workflows/`, `.env.example`, `README.md`,
top-level `.gitignore` additions.

## Scope
- Python: FastAPI + Pydantic, SQLAlchemy + Alembic, pytest; `uv` for deps with a lockfile.
- Web: Next.js + React + TypeScript + Tailwind, Vitest, Playwright installed (one smoke test).
- `compose.yaml`: postgres, redis. API and web run as separate processes.
- Makefile targets: `dev`, `test`, `lint`, `contracts` (stub that exports OpenAPI to
  `packages/contracts/openapi.json`), `eval-smoke` (stub, exits 0 with "no suites yet").
- CI: lint + `make test`; fails if `packages/contracts/openapi.json` is stale.
- Pin versions; don't claim "latest".

## Invariants
- No secrets committed; `.env.example` lists keys with empty values.
- Tests make no network calls.

## Validation commands
```
make test
make contracts && git diff --exit-code packages/contracts
```

## Excluded scope
Auth, domain models, any provider code, any UI beyond a placeholder page.

## Handoff checklist
- [ ] Commands above pass locally
- [ ] Update `AGENTS.md` "Commands" section with real commands
- [ ] `docs/handoffs/CURRENT.md` + LEDGER updated
