# Handoff — main after T-005 spec

- **Updated:** 2026-09-26 by Claude Code
- **Branch / worktree:** main @ ~/code/market-sentinel
- **Status:** T-005 `ready`; T-007 awaiting Codex review

## Next step (exact — the next agent starts here)
- **Codex**, first: review T-007 in `~/code/ms-wt/api` (`git checkout --detach origin/task/T-007-today`),
  following the "Next step" in that branch's `docs/handoffs/CURRENT.md`. Report findings to the
  user; do not commit to T-007.
- **Codex**, then in a fresh session: in `~/code/ms-wt/api`, `git checkout -b task/T-005-instrument-resolution origin/main`
  and implement `docs/tasks/T-005-instrument-resolution.md`, starting with planned commit 1
  (synthetic instrument master in `evals/fixtures/generate.py`).

## Done this session
- Wrote `docs/tasks/T-005-instrument-resolution.md`: exact, date-effective symbol lookup against a
  generated synthetic instrument master; per-row `resolution` object replaces `"pending"`;
  `GET /instruments?symbol=` lookup; select/clear endpoints for ambiguous and typo rows.
- Ledger: T-005 → `ready`.

## Tests run
- None (docs only).

## Contract changes proposed (not applied)
- T-007 proposes `issue.schema.json` (v1.1 candidate); see its branch handoff.
- T-005 will propose `instrument` and `symbol_mapping` schemas; bundle both into one v1.1 bump.

## Unresolved / assumptions
- T-005 changes the `resolution` field shape in the import preview API (string → object). Nothing
  consumes it yet; T-007 is fixture-driven.
- `as_of` = UTC date of `received_at`. Whether confirm (later) re-resolves at confirm time is open.
- The app's default instrument repository reads `evals/fixtures/instruments/` until T-008 brings
  provider reference data.
- Carried over: upload request-size limit needed before exposing `/imports`; previews are
  process-local; T-007 merge will conflict on `CURRENT.md`/`LEDGER.md` (consider one handoff file
  per task); horizon enum (T-000); JEV access (blocks T-009); T-009 injection variant on usable
  data; consumers must enable date-time format checking (ADR-001 §3).
