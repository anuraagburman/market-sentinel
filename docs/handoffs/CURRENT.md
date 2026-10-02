# Handoff — T-012 merged; T-013 back to Claude Code with review changes

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** main (merge `76fd6ff`, done from the main checkout). T-013 lives on `task/T-013-contracts-v1-1`.
- **Status:** T-012 `merged` · T-013 `changes_requested`

## Next step (exact — the next agent starts here)
- **Codex** (`~/code/ms-wt/api`): release the T-013 branch (`git switch --detach origin/main`) so Claude Code can
  check it out. Codex's lane is otherwise free. T-008 (provider adapters) is next once it has a spec.
- **Claude Code** (`~/code/ms-wt/web`): `git fetch && git switch task/T-013-contracts-v1-1 && git merge origin/main`
  (T-012 regenerated `packages/contracts/openapi.json`, so resolve any conflict there by re-running `make contracts`).
  Then fix the two Codex findings in the T-013 branch handoff, writing the regression tests first:
  1. Pattern anchors accept a trailing newline (`symbol_mapping.schema.json:13`, `common.schema.json:35,40`).
  2. `valuation.schema.json` requires a positive `price.value`, but the API producer still returns 200 for zero
     or negative closes. Producer validation is in the api lane, so either agree on an owner in the handoff or
     scope the schema to what the producer guarantees.

## Done this session
- Re-reviewed T-012 fix commits `ee75abb` (migration URL isolation, guard on non-`_test` `DATABASE_URL`) and
  `effdd5a` (NUL rejected before storage, 503 limited to connection, pool-timeout and retry-exhausted failures).
  Both blockers are fixed.
- Approved two deviations from the spec:
  - A NUL in an upload now returns `422 invalid_csv` (a tightening of T-011).
  - `IntegrityError` / `DataError` return 500, not 503. A 503 tells the client to retry, and these errors mean a
    bug.
- Merged `task/T-012-postgres-store` with `--no-ff` (`76fd6ff`). The only conflict was the LEDGER lanes line.
  Apart from docs, the merge tree is identical to the reviewed tip `b93fd5c`.

## Tests run (reviewed tip `b93fd5c`, scratch worktree, DB `sentinel_review_test`)
- `pytest apps/api/tests packages/contracts/tests evals/tests` → 380 passed, 0 skipped (Postgres included).
- Repository, API, worker and operations suites run 8 times → 65 passed each run (520 total).
- `alembic check` → no new upgrade operations.
- `python -m app.export_openapi` + `git diff --exit-code packages/contracts` → no diff.
- `ruff check` and `ruff format --check` → clean.
- `CI=true` with no `TEST_DATABASE_URL` → UsageError, so CI can't go green by skipping. A non-`_test`
  `DATABASE_URL` → UsageError.
- `grep -rn IMPORT_LOCK apps/api/app apps/api/tests` → nothing.
- Vitest and ESLint not run, because the branch has no `apps/web` changes.

## Contract changes proposed (not applied)
- none (T-012 changed only OpenAPI `responses`, adding 503, through `make contracts`)

## Unresolved / assumptions
- T-012 follow-ups (no task yet; fold them into the next api-lane store task):
  - UNIQUE on `import_confirmations.portfolio_version_id`.
  - Composite (`tenant_id`, `previous_version_id`) FK.
  - `seed_fixture` refuses when a tenant head already exists. Today it chains the fixture on top of real data.
  - Prune `InMemoryPreviewRepository._locks`.
  - `PostgresPreviewRepository.write` picks insert or update implicitly and doesn't check that the update hit a
    row. Use an explicit upsert or assert `rowcount == 1`.
  - `.env.example` defaults `MS_ENV=dev`, which weakens the seed guard if the file is copied as-is.
- Running tests with a dev `DATABASE_URL` exported in your shell now fails by design. Unset it or point it at a
  `_test` database.
- Carried over:
  - Per-tenant idempotency keys at auth time.
  - Managed-Postgres settings and observation persistence.
  - Upload request-size limit.
  - Web grouping of `row_has_errors` + `row_unresolved`.
  - Provider adapters reject non-positive closes (T-008); this also bears on T-013 finding 2.
  - T-005 nits.
  - JEV pricing sits outside the $25 model cap (ADR-003 Open).
  - Today parses only UTC `Z` timestamps.
