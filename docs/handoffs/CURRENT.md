# Handoff — main after T-004 merge

- **Updated:** 2026-09-26 by Claude Code
- **Branch / worktree:** main @ ~/code/market-sentinel
- **Status:** T-004 merged; T-007 awaiting Codex review; T-005 needs a spec

## Next step (exact — the next agent starts here)
In parallel:
- **Codex** reviews T-007 in `~/code/ms-wt/api`: `git checkout --detach origin/task/T-007-today`
  (the branch itself is checked out in `~/code/ms-wt/web`), then follow the "Next step" in that
  branch's `docs/handoffs/CURRENT.md`. Write findings to the user; do not commit to T-007.
- **Claude Code** writes `docs/tasks/T-005-instrument-resolution.md` on `main` and moves T-005 to
  `ready` in the ledger. Input: T-004's preview (`resolution: "pending"`, `parsed.symbol`).

## Done this session
- Reviewed T-004 twice (44024cb, 4d77997). Codex fixed: browser CSV MIME variants with `.csv`
  filenames, one issue per formula cell, `blank_row` warning, `negative_cost_basis` error.
- Merged T-004 to `main` with `--no-ff`; ledger row set to `merged`.

## Tests run
- At 4d77997: `make test` → 210 Python + 1 Vitest passed; `make lint` → pass;
  `make contracts && git diff --exit-code packages/contracts` → pass.

## Contract changes proposed (not applied)
- T-007 proposes `issue.schema.json` (v1.1 candidate); see its branch handoff.

## Unresolved / assumptions
- Upload size is checked after Starlette receives the whole body; a request-size limit is needed at
  deploy time before the endpoint is exposed.
- Import previews are process-local until persistence/`confirm` lands.
- T-007 merge will conflict on `CURRENT.md` and `LEDGER.md` (both edited on branches); resolve by hand.
  Consider one handoff file per task.
- Still open from before: horizon enum (T-000), JEV access (blocks T-009), T-009 injection variant on
  usable data, consumers must enable date-time format checking (ADR-001 §3).
