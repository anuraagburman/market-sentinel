# Handoff — T-008 provider adapters spec ready

- **Updated:** 2026-10-02 by Codex
- **Branch / worktree:** task/T-008-provider-adapters @ ~/code/ms-wt/api
- **Status:** ready_for_review (spec only; ledger ready)

## Next step (exact — the next agent starts here)
Review `docs/tasks/T-008-provider-adapters.md`, then implement its non-positive close guard and
passing domain/API/conformance regressions first. Remove `test_non_positive_close_conforms` and its
strict xfail as specified. Implementation has not started.

## Done this session
- Switched api from T-013 to detached origin/main at 9a9eb1c, then created the T-008 task branch.
- Wrote provider adapter spec: Alpaca daily bars, SEC submissions, bounded transport, provenance,
  cutoff rules, synthetic fixtures, explicit coverage and owned paths.
- Spec includes adapter rejection and valuation defense for zero/negative closes, without loosening contracts.
- Updated T-008 ledger to ready. FRED, persistence and live API wiring are explicit follow-ups.

## Tests run
- `git diff --check` → passed.
- Documentation-only session; runtime tests not run. Implementation validation is specified in T-008.

## Contract changes proposed (not applied)
- None for T-008; existing v1.1 remains strict.
- Carry-forward optional v1.2: anchor remaining v1 patterns to reject trailing newlines in Python.

## Unresolved / assumptions
- T-012 follow-ups (no task yet; fold them into the next api-lane store task):
  - UNIQUE on `import_confirmations.portfolio_version_id`.
  - Composite (`tenant_id`, `previous_version_id`) FK.
  - `seed_fixture` refuses when a tenant head already exists. Today it chains the fixture on top of real data.
  - Prune `InMemoryPreviewRepository._locks`.
  - `PostgresPreviewRepository.write` picks insert or update implicitly and doesn't check that the update hit a
    row. Use an explicit upsert or assert `rowcount == 1`.
  - `.env.example` defaults `MS_ENV=dev`, which weakens the seed guard if the file is copied as-is.
- Running tests with a dev `DATABASE_URL` exported in your shell fails by design. Unset it or point it at a
  `_test` database. Codex's review run skipped the 50 Postgres tests because no `TEST_DATABASE_URL` was set.
- Carry forward: /briefs projection formatter (Today fixtures with `brief.issues`), codegen, upload size limit,
  per-tenant keys, observation persistence, web grouping of `row_has_errors` + `row_unresolved`.
