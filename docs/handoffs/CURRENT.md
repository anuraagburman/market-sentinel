# Handoff — main after T-003 merge

- **Updated:** 2026-09-26 by Claude Code
- **Branch / worktree:** main @ ~/code/market-sentinel
- **Status:** main pushed to GitHub; T-004 and T-007 ready

## Next step (exact — the next agent starts here)
In parallel: Codex implements T-004 (`docs/tasks/T-004-csv-import.md`) in `~/code/ms-wt/api` on
`task/T-004-csv-import`; Claude Code implements T-007 (`docs/tasks/T-007-today-page.md`) in
`~/code/ms-wt/web` on `task/T-007-today`. Each writes its own handoff on its branch.

## Done this session
- Merged T-001 (skeleton), T-002 (contracts v1), T-003 (fixtures). All reviewed cross-agent.
- Published to https://github.com/anuraagburman/market-sentinel (public; blueprint PDF purged from history, gitignored).
- Wrote T-004 and T-007 specs.
- T-003: 19-position synthetic portfolio (20 raw rows, five import cases), ten adversarial packets,
  deterministic generator, `make test` runs contracts + fixtures suites.

## Tests run
- See the T-003 merge commit message for the results on main.

## Contract changes proposed (not applied)
- none

## Unresolved / assumptions
- T-009 should add an injection variant on **usable** data (packet 07 only exercises the unusable gate,
  so the injected text never reaches a judgment stage).
- Workflow: parallel branches conflict on CURRENT.md and LEDGER.md. Consider one handoff file per task.
- Horizon enum `swing | multiweek` still to be confirmed in T-000. JEV access unconfirmed (blocks T-009).
- Consumers must enable date-time format checking (ADR-001 §3).
