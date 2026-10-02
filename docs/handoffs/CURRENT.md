# Handoff — T-011 merged; next T-012 spec and T-013 contracts

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** main @ ~/code/market-sentinel (review done from ~/code/ms-wt/web, detached)
- **Status:** T-011 `merged` (`b8c5dc4`, `--no-ff`); T-012 and T-013 `backlog`

## Next step (exact — the next agent starts here)
- **Claude Code:** write `docs/tasks/T-012-postgres-store.md` (move T-012 to `ready`). It must carry the
  T-012 requirements listed under "Unresolved" below. Then start T-013 (contracts v1.1), which Claude Code owns.
- **Codex:** idle until the T-012 spec lands. `~/code/ms-wt/api` can be reset to `origin/main`.

## Done this session
- Reviewed `task/T-011-import-confirm` (`030a4a6`) against `docs/tasks/T-011-import-confirm.md`.
  Focus areas: transaction boundaries, idempotency precedence, and the reusable repository suite. No
  blocking findings. Every endpoint, blocker code, status mapping and acceptance step in the spec is implemented and tested.
  - Idempotency precedence: key receipt → import receipt → revision → readiness → store.confirm. The store
    re-checks key/import under its lock, so a race returns the existing receipt (200, 409 or 422).
  - The store validates before writing and writes version, positions, receipt and predecessor under one lock.
    Reads are deep copies, and there is no update/delete.
  - The repository suite is parametrized (`memory` only), and T-012 adds its factory there.
- Merged to main with `--no-ff` and pushed.

## Tests run
- `make test` → 324 Python + 64 web passed (on the branch; main was the merge base, so the tree is identical).
- `make lint` → passed. `make contracts && git diff --exit-code packages/contracts` → clean.
- Confirm API + repository suites run 8× in a row → 19 passed each time (concurrency tests stable).

## Contract changes proposed (not applied)
- Unchanged and tracked as T-013: `valuation.schema.json` (T-006 `cc8f1f5`), `issue.schema.json` +
  `brief.coverage.pending_sources` (T-007 `3e744e2`), `instrument.schema.json` /
  `symbol_mapping.schema.json` (T-005 `f0caae1`). Consider whether confirm/readiness shapes need schemas too.

## Unresolved / assumptions
- **For the T-012 spec:**
  - Pass `apps/api/tests/test_confirm_repository.py`. Unique `import_id` and unique `idempotency_key`.
    Version, positions, receipt and predecessor selection go in one transaction. A key or import
    collision returns the existing receipt. A validation failure writes nothing.
  - Replace the process-wide `IMPORT_LOCK` with transactional coordination of preview revision, row
    edits and confirm. Previews must persist too, or stale-edit protection breaks across workers.
  - Seeding: the default store is seeded with the synthetic fixture version for the placeholder tenant.
    The first real confirm in a running server therefore gets `previous_version_id` = the fixture id.
    Postgres should not seed production data. Keep the fixture only for tests/dev.
- Review nits (non-blocking, fold into T-012):
  - The async `upload_import` takes the threading `IMPORT_LOCK` on the event loop, so it blocks the loop
    while a sync route holds the lock.
  - `confirm_import` computes `previous` that the store then overrides. The seed and the tests read
    `FilePortfolioRepository._version`, a private attribute.
  - `test_edit_cannot_cross_confirmation_transaction` passes even if the edit arrives after confirm,
    because the race isn't forced.
  - An error row that is also unresolved shows both `row_has_errors` and `row_unresolved`. That is allowed
    by the spec table, but the UI should group blockers per row.
- Carried over: provider adapters should reject non-positive closes (T-008); T-005 nits (`domain/instruments.py`
  imports from `services/`; bare `assert`; local `UTC` import); upload request-size limit before exposing
  `/imports`; JEV pricing outside the $25 model cap (ADR-003 Open); T-009 injection variant on usable data;
  consumers must enable date-time format checking (ADR-001 §3); Today parses only UTC `Z` timestamps.
