# Handoff — T-013 re-review: producer finding remains

- **Updated:** 2026-10-02 by Codex
- **Branch / worktree:** task/T-013-contracts-v1-1 @ ~/code/ms-wt/api
- **Status:** changes_requested

## Next step (exact — the next agent starts here)
Resolve the non-positive-close producer conformance finding with the API owner, or obtain explicit acceptance of merging with this known gap. Keep the strict schema per the recorded user decision. Do not merge under the current instruction to merge only if both findings are resolved.

## Done this session
- Fast-forwarded the local T-013 branch from 09a8046 to f6a98ab. Both worktrees were initially detached; the pull succeeded after checking out T-013 in api. Web remains detached.
- Reviewed `git diff 09a8046..origin/task/T-013-contracts-v1-1` against the two findings.
- Trailing-newline finding resolved: new v1.1 patterns reject final newlines and regression fixtures cover money, weight, symbol and date.
- Non-positive-close finding remains: API returns HTTP 200 with a price that violates the strict schema. Strict xfail tests track the mismatch; they do not correct producer behavior. The decision to retain the strict schema is honored.
- No merge performed because the user's merge condition requires both findings resolved.

## Tests run
- `make test` → 385 Python passed, 50 skipped (Postgres tests unavailable without test database configuration), 2 xfailed; 64 Vitest passed.
- `make lint` → passed (Ruff, ESLint, TypeScript).

## Contract changes proposed (not applied)
- Optional v1.2: anchor the v1 patterns (`uuid`, `utc_timestamp`, `decimal_string`,
  `positive_decimal_string`, `currency`, `sha256`, feed version) the same way. Under ECMA-262 this narrows
  nothing; it only makes Python agree.

## Unresolved / assumptions
- Follow-up for Codex (fold into T-008): the valuation producer treats a non-positive close as unavailable
  (`no_price`, or a dedicated reason via a contract bump), and the strict xfail is removed. This is the T-008
  carry-forward "provider non-positive close rejection".
- T-012 is merged (`76fd6ff`) and merged into this branch; its tests pass here.
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
- Carry forward: /briefs projection formatter, codegen, upload size limit, per-tenant keys, observation persistence.
