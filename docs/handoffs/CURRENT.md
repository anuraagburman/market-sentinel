# Handoff — T-012 review blockers fixed

- **Updated:** 2026-10-02 by Codex
- **Branch / worktree:** task/T-012-postgres-store @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code: re-review commits ee75abb and effdd5a against the two T-012 blockers; then approve for merge if clean. T-013 remains on its separate branch, ready for review per its prior handoff.

## Done this session
- Blocker 1 (`ee75abb`): Alembic prefers an explicit config URL. Empty ini URL preserves DATABASE_URL fallback for CLI usage. Test collection refuses a non-_test DATABASE_URL as well as a non-_test TEST_DATABASE_URL.
- Migration regression failed first by attempting the conflicting environment endpoint; passed after the fix. Upgrade/downgrade/check lifecycle also passes.
- Blocker 2 (`effdd5a`): parser rejects NUL anywhere in decoded CSV before storage with 422 invalid_csv and message "CSV must not contain NUL bytes." Both stores return identical Problems for NUL in symbol, unknown cell, and header.
- Ten blocker-2 regression cases failed first, then passed. IntegrityError/DataError propagate as server errors rather than suggesting retry later. 503 is limited to OperationalError, InterfaceError and pool TimeoutError; transaction retry policy remains unchanged.
- Optional changes deferred; no schema migration added.

## Tests run
- `TEST_DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test make test` → 380 pytest passed (Postgres included), 64 Vitest passed.
- `make lint` → passed.
- `make contracts` and `git diff --exit-code packages/contracts` → passed, no diff.
- `cd apps/api && DATABASE_URL=postgresql+psycopg://sentinel@localhost:5432/sentinel_test uv run --locked alembic check` → no new upgrade operations.
- Repository/API/worker/operations suites 8× → 65 passed each run, 520 total; includes forced edit-vs-confirm on both stores, worker races and transaction retries.
- Non-_test DATABASE_URL collection check → refused with UsageError (expected exit 4), before database access.
- Targeted migration suite → 2 passed; targeted API/operations → 54 passed.
- Existing Starlette/AnyIO deprecation warning only.

## Contract changes proposed (not applied)
- NUL uploads now return existing Problem shape/code `422 invalid_csv` rather than a preview. This is a T-011 behavior tightening, flagged for reviewer approval; no schema or OpenAPI change is needed because 422 Problem already exists.

## Unresolved / assumptions
- Follow-ups requested by review: UNIQUE on import_confirmations.portfolio_version_id; composite (tenant_id, previous_version_id) FK; seed_fixture refusal when a tenant head already exists; prune InMemoryPreviewRepository._locks.
- Alembic CLI now requires DATABASE_URL or an explicit configured URL (no implicit dev database default).
- Integrity/Data errors indicate an unexpected invariant or validation bug and surface as 500; they must not advertise transient availability/retry.
- Carried forward: per-tenant idempotency keys at auth time, managed-Postgres settings, observation persistence; upload request-size limit and web grouping of row_has_errors/row_unresolved remain separate work.
