# Handoff — T-011 import confirmation ready for review

- **Updated:** 2026-09-27 09:02 +08 by Codex
- **Branch / worktree:** task/T-011-import-confirm @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
- **Claude Code:** review `task/T-011-import-confirm` against `docs/tasks/T-011-import-confirm.md`,
  focusing on transaction boundaries, idempotency precedence, and the reusable repository suite.
  Review from your own worktree; do not edit the API worktree concurrently.
- After approval, merge with `--no-ff` and push main. This session did not merge.

## Done this session
- Fetched origin, created the requested task branch from origin/main, and fast-forwarded
  `~/code/market-sentinel` to `ff060ce`.
- Added pure row-order blockers and exact string/null portfolio mapping; confirm never re-resolves.
- Added revisioned row exclusions, auto-excluded blank rows, computed readiness, and confirmation
  metadata derived from the portfolio store. Computed fields are not persisted in preview snapshots.
- Added atomic in-memory portfolio storage, seeded from the validated fixture, with copies on reads,
  unique import/key receipts, and predecessor selection under the write lock.
- Added idempotent confirm and portfolio snapshot GET, post-confirm edit rejection, and generated OpenAPI.
  Cash/account fields remain absent when not supplied; null cost basis stays explicit.
- Added fixture-to-valuation acceptance, retry/key reuse, concurrency, edit/confirm serialization,
  exclusion properties, removed-instrument, clock, and reusable repository contract tests.
- Updated the existing resolution round-trip assertion to require revision 6 while retaining equality
  for all other fields. Failed row decisions still leave revision unchanged.

## Tests run
- Initial pure-domain tests failed because the confirm module did not exist (expected red step).
- Targeted confirmation and resolution suite → 35 passed.
- `make test` → 324 Python tests and 64 web tests passed.
- `make lint` → Ruff checks/format, ESLint, Next type generation, and TypeScript passed.
- `make contracts && git diff --exit-code packages/contracts` → passed; generated contract is stable.
- Existing Starlette/AnyIO deprecation warning remains; no live data/model APIs or database used.

## Contract changes proposed (not applied)
- JSON schemas unchanged. T-013 still owns the v1.1 additions carried from T-005/T-006/T-007:
  valuation, issue, instrument, symbol_mapping, and brief.coverage.pending_sources.

## Unresolved / assumptions
- T-012: implement the same repository contract suite (`test_confirm_repository.py`) with Postgres.
  Enforce unique `import_id` and `idempotency_key`; version, positions, receipt, and tenant predecessor
  selection must share one transaction. Key collisions return the existing receipt for service-level
  200/409/422 mapping. Validation failures must write nothing.
- T-012 must also replace process-wide `IMPORT_LOCK` with transactional coordination of preview
  revision/row edits and confirmation. A portfolio-store transaction alone cannot prevent stale
  preview edits. The current global lock serializes API operations within this process only.
- Store and previews are temporary, lost on restart, and not shared across workers. The placeholder
  tenant remains the fixture tenant. No-op successful decisions increment revision.
- Authentication, Postgres, cash entry, aggregation, and the import UI remain outside T-011.
- Carried forward: provider adapters should reject non-positive closes (T-008); request-size limits
  before exposing uploads; JEV pricing outside the $25 model cap (ADR-003 Open); T-009 injection
  variant on usable data; consumers must enable date-time format checking (ADR-001 §3).
