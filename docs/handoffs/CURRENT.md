# Handoff — main after T-006 merge

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** main (merge built in ~/code/ms-wt/web, pushed to origin/main; `~/code/ms-wt/api`
  and `~/code/market-sentinel` need `git pull --ff-only` / a fresh branch from `origin/main`)
- **Status:** T-006 `merged`; no task `ready`

## Next step (exact — the next agent starts here)
- **Claude Code**, in a fresh session: write `docs/tasks/T-011-import-confirm.md` (import confirm →
  immutable PortfolioVersion) so Codex can start it, then mark T-011 `ready` in the ledger.
  Before that, or with it, decide whether to land the contracts v1.1 bump (below).

## Done this session
- Reviewed `origin/main...task/T-006-valuation` @ `99fabc3` against the task file. One finding:
  `unit_mismatch` returned a non-null price, and since `Price` has no `unit`, a USD row would have shown a
  CAD number. Codex fixed it in `cc8f1f5` (price null + regression assertion); verified.
- Merged with `--no-ff`.

## Tests run
- On the T-006 head `99fabc3`: `make test` → pytest 300 passed, Vitest 64 passed; `make lint` passed;
  `make contracts` byte-identical.
- On the merge result: `make test` → 300 + 64 passed; `make lint` passed; `make contracts` byte-identical.

## Contract changes proposed (not applied)
- One v1.1 bump should bundle: T-006's `valuation.schema.json` (full shape in the T-006 handoff,
  commit `cc8f1f5`), T-007's `issue.schema.json` and `brief.coverage.pending_sources`, and T-005's
  `instrument.schema.json` / `symbol_mapping.schema.json` (T-005 handoff `f0caae1`, T-007 handoff `3e744e2`).

## Unresolved / assumptions
- T-006 follow-up (for T-008): a `0` or negative close passes observation validation and is valued as
  a real price (a `0` close → market value `0.00`, counted as priced, weight `no_priced_value`).
  Provider adapters should reject non-positive closes.
- T-006: `Price.value` keeps the observation's original precision; an empty confirmed portfolio with
  USD cash has `total_value` = cash; repositories are process-lifetime synthetic snapshots until T-011.
- T-005 review nits (non-blocking): `domain/instruments.py` imports `InstrumentRepository` from
  `services/` (move into `domain/` by T-008); bare `assert` in resolver code; function-local
  `from datetime import UTC` in `routes/instruments.py`.
- T-005: display-symbol rule for several active aliases is labels-only; future-only mappings return
  `symbol_not_found`; master data is a process-lifetime snapshot; whether confirm re-resolves is open (T-011).
- T-007: Today parses only UTC `Z` timestamps; stale = `cutoff` Friday / `published_at` Monday (confirm);
  Ajv runs with `strictTypes`/`strictRequired` off for if/then subschemas.
- Carried over: upload request-size limit before exposing `/imports`; previews are process-local;
  one handoff file per task would avoid merge conflicts here; JEV pricing outside the $25 model cap
  (ADR-003 Open); T-009 injection variant on usable data; consumers must enable date-time format
  checking (ADR-001 §3).
