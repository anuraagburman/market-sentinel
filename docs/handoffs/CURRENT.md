# Handoff — T-012 Postgres store checkpoint

- **Updated:** 2026-10-02 10:04 Asia/Singapore by Codex
- **Branch / worktree:** task/T-012-postgres-store @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code: from your own worktree, review `task/T-012-postgres-store` against
`docs/tasks/T-012-postgres-store.md`. Focus on preview → tenant-head lock order,
collision rollback, complete-operation retries, migration constraints, and lossless
document reconstruction. After approval, merge with `--no-ff` and push main.

## Done this session
- Checked the active task, template, ledger, branch, and working tree at the user's checkpoint request.
- Working tree was clean at `c4e96ea`; no implementation work was pending.
- Overwrote this handoff from the template and updated the T-012 ledger checkpoint note.
- T-012 implementation and its prior validation remain ready for review; this session did not merge.

## Tests run
- `git status --short --branch` → clean working tree on the expected task branch before checkpoint edits.
- No code tests rerun: this checkpoint changes handoff and ledger documentation only.
- Prior implementation-session results retained below:
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
