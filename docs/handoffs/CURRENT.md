# Handoff — T-013 merged; producer close gap goes to T-008

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** main (T-013 merged with `--no-ff` from ~/code/ms-wt/web, detached on origin/main)
- **Status:** T-013 `merged`

## Next step (exact — the next agent starts here)
Codex (`~/code/ms-wt/api`): `git switch --detach origin/main`, then spec T-008 (provider adapters). The spec must
include the valuation producer treating a non-positive close as unavailable, and removing the strict xfail
`test_non_positive_close_conforms` in `apps/api/tests/test_contracts_v1_1.py`.

## Done this session
- Fixed both Codex T-013 findings (`c5eacd0`, `519d67f`, `aca653d`). Codex re-reviewed (`4613e88`): the newline
  fix is resolved, and the producer close gap remains by design.
- Anuraag explicitly accepted merging with that gap tracked by the strict xfail (the strict schema is kept).
- Merged `task/T-013-contracts-v1-1` into main with `--no-ff`, with no conflicts. The merge tree is identical to
  the reviewed tip `4613e88`.

## Tests run (merge result, local Postgres `sentinel_test`)
- `make test` → 435 pytest passed, 2 xfailed (the tracked producer gap), 0 skipped; 64 Vitest passed.
- `make lint` → exit 0.
- `gen_examples.py` + `make contracts` → no diff.

## Contract changes proposed (not applied)
- Optional v1.2: anchor the v1 patterns (`uuid`, `utc_timestamp`, `decimal_string`,
  `positive_decimal_string`, `currency`, `sha256`, feed version) with `$(?!\n)` as v1.1 does. Under ECMA-262
  this narrows nothing; it only makes Python agree.

## Unresolved / assumptions
- T-008 must close the non-positive close gap (see Next step). This is the T-008 carry-forward "provider
  non-positive close rejection".
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
