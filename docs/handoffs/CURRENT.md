# Handoff — T-012 spec ready; Codex implements T-012, Claude Code starts T-013

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** main (spec written from ~/code/ms-wt/web, detached at origin/main)
- **Status:** T-012 `ready` (spec `c44c2b0`); T-013 `backlog`

## Next step (exact — the next agent starts here)
- **Codex** (`~/code/ms-wt/api`): `git fetch && git switch -c task/T-012-postgres-store origin/main`,
  read `docs/tasks/T-012-postgres-store.md`, and implement it in its planned commit order. CI must run the
  Postgres tests (not skip them).
- **Claude Code** (`~/code/ms-wt/web`): write the T-013 spec (contracts v1.1) and implement it on
  `task/T-013-contracts-v1-1`. It has no path overlap with T-012. T-012 changes no JSON schemas.

## Done this session
- Wrote `docs/tasks/T-012-postgres-store.md`. It covers every T-012 requirement from the T-011 handoff:
  - The repository contract runs on memory and Postgres.
  - Unique `import_id` and `idempotency_key`.
  - Version, positions, receipt and predecessor go in one transaction behind a tenant-head row lock, with
    UNIQUE (`tenant_id`, `previous_version_id`) NULLS NOT DISTINCT as a backstop.
  - A collision returns the existing receipt, and a validation failure writes nothing.
  - Previews are persisted. A per-import unit of work (`SELECT … FOR UPDATE` on the preview row) replaces
    `IMPORT_LOCK`, with lock order preview → tenant head.
  - Postgres is never seeded; `seed_fixture` is explicit and limited to dev/test.
  - All four T-011 review nits are folded in. Row-blocker grouping goes to the web lane.
- Added requirements the handoff didn't list:
  - Round-trip fidelity (decimal and timestamp text, absent vs null `cash`).
  - Database-level immutability triggers.
  - Startup fails rather than falling back to memory.
  - `503 store_unavailable`.
  - A `_test`-suffix guard on the test database. With `CI=true`, a missing `TEST_DATABASE_URL` fails.
  - Cross-worker and durability tests.
  - Alembic up/down/check.
- Ledger: T-012 → `ready`.

## Tests run
- None. This was a docs-only change, with no code touched.

## Contract changes proposed (not applied)
- Still T-013: `valuation.schema.json` (T-006 `cc8f1f5`), `issue.schema.json` +
  `brief.coverage.pending_sources` (T-007 `3e744e2`), `instrument.schema.json` /
  `symbol_mapping.schema.json` (T-005 `f0caae1`). Consider whether confirm/readiness shapes need schemas too.
- T-012 adds `503 store_unavailable` to OpenAPI responses only, through `make contracts`.

## Unresolved / assumptions
- The spec chooses SQLAlchemy Core (not the ORM) and READ COMMITTED isolation with explicit row locks.
  Codex may challenge either choice in its handoff if the implementation shows a problem.
- Idempotency keys stay globally unique until auth exists. Making them per-tenant is a later migration.
- Web lane (later): group `row_has_errors` + `row_unresolved` per row in the import UI.
- Carried over:
  - Provider adapters should reject non-positive closes (T-008).
  - T-005 nits: `domain/instruments.py` imports from `services/`; a bare `assert`; a local `UTC` import.
  - Add an upload request-size limit before exposing `/imports`.
  - JEV pricing sits outside the $25 model cap (ADR-003 Open).
  - T-009 injection variant on usable data.
  - Consumers must enable date-time format checking (ADR-001 §3).
  - Today parses only UTC `Z` timestamps.
