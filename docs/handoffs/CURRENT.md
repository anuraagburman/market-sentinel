# Handoff — T-012 Postgres store ready for review

- **Updated:** 2026-10-02 by Codex
- **Branch / worktree:** task/T-012-postgres-store @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
- **Claude Code:** review `task/T-012-postgres-store` against `docs/tasks/T-012-postgres-store.md`
  from your own worktree. Focus on preview → tenant-head lock order, collision rollback,
  complete-operation retries, migration constraints, and lossless document reconstruction.
  After approval, merge with `--no-ff` and push main. This session did not merge.
- The web lane can continue T-013 independently; T-012 changes only generated OpenAPI, not JSON schemas.

## Done this session
- Fetched origin and created the requested task branch from origin/main.
- Implemented the planned eight code/test commits, followed by this handoff commit.
- Added lazy SQLAlchemy Core engine, READ COMMITTED isolation, a 16-connection pool,
  startup connectivity/head checks, lifespan disposal, and guarded test database provisioning.
- Added the first reversible Alembic migration: previews, tenant heads, versions, positions,
  and receipts; unique import/key constraints; NULLS NOT DISTINCT linear-chain backstop;
  database UPDATE/DELETE immutability triggers.
- Persisted original JSON documents alongside typed timestamps and unrestricted numeric columns,
  preserving decimal/timestamp text, row order, explicit nulls and absent fields exactly.
- Added portfolio and preview repositories. Head selection and portfolio/position/receipt writes
  share a transaction. Receipt collisions roll back the entire attempt, including a newly created
  tenant head, and return the winner. Only receipt uniqueness violations are recovered.
- Replaced the process-wide import lock with per-import transactions: memory per-import locks;
  Postgres preview FOR UPDATE then tenant-head lock on one connection. CSV parsing/storage runs
  off the event loop. The store alone selects the predecessor; fixture version has a public accessor.
- Added retries for whole operations on serialization failure/deadlock (at most three attempts),
  store failures return 503 store_unavailable, and generated the affected OpenAPI responses.
- Wired DATABASE_URL with explicit logged memory mode when unset; configured databases never
  silently fall back. Fresh Postgres is empty. Added explicit idempotent dev/test fixture seed,
  make seed-dev, and migrations before make dev starts the API.
- Configured CI Postgres 17.4 and TEST_DATABASE_URL. CI collection fails without that URL;
  local tests skip visibly when it is absent. Test database names must end in _test.
- Added both-store API/repository contracts, forced races, independent-worker coordination,
  restart durability, fidelity, migrations, immutability, startup, seeding, injected rollback/retry,
  and forced global-key collision tests. Updated developer instructions in README.

## Tests run
- Planned red repository step: four memory cases passed; four Postgres cases failed because the
  repository module did not exist. Implementation subsequently passed all eight unchanged cases.
- `docker compose up -d --wait postgres` → local Postgres healthy.
- `TEST_DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test make test`
  → **369 Python tests and 64 web tests passed**, no Postgres skips.
- `make lint` → Ruff checks/format, ESLint, Next type generation and TypeScript passed.
- `make contracts && git diff --exit-code packages/contracts` → passed, generated contract stable.
- `cd apps/api && DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test uv run alembic check`
  → no new upgrade operations detected.
- Repository + API + cross-worker/durability suites repeated **8 times** → **41 passed per run,
  328 total**. Both-store forced edit/confirm race passed in each run.
- Migration test includes upgrade, downgrade to base (no application tables), upgrade again and check.
- `rg IMPORT_LOCK apps/api` → no matches.
- Existing Starlette/AnyIO deprecation warning remains. No live model or data provider calls.
- GitHub CI is configured but has not been observed running in this local session.

## Contract changes proposed (not applied)
- T-013 retains ownership of JSON schema v1.1 additions (valuation, issue, instrument,
  symbol_mapping, brief.coverage.pending_sources). T-012 changed generated OpenAPI responses only.

## Unresolved / assumptions
- Placeholder fixture tenant remains until auth. Idempotency keys are globally unique; auth must
  migrate them to per-tenant uniqueness and add authorization boundaries.
- Managed-Postgres deployment/pooler settings and observation persistence remain later tasks.
  Observation and instrument repositories still use synthetic files. Memory mode remains temporary.
- Original model documents are stored with relational values to preserve wire fidelity; future
  migrations must maintain both representations. Confirmed records are immutable at the DB layer.
- Local Docker Postgres remains running for reviewer validation.
- Carried forward: request-size limit before exposing uploads; provider non-positive close rejection
  (T-008); JEV pricing outside the $25 model cap; T-009 injection variant on usable data; date-time
  format checking by consumers; UTC Z-only timestamp parsing; import blocker grouping in web lane.
