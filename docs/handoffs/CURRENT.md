# Handoff — T-011 spec written

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** main (spec commit made in ~/code/ms-wt/web, pushed to origin/main)
- **Status:** T-011 `ready`; T-012 and T-013 added as `backlog`

## Next step (exact — the next agent starts here)
- **Codex**, in `~/code/ms-wt/api`: `git fetch && git switch -c task/T-011-import-confirm origin/main`,
  read `docs/tasks/T-011-import-confirm.md`, and start with planned commit 1 (failing confirm-rule tests).
- **Claude Code** (parallel, no path overlap): write the T-013 contracts v1.1 spec, or implement it directly
  since Claude Code owns contracts (T-002).

## Done this session
- Wrote `docs/tasks/T-011-import-confirm.md`. Scope decisions made there:
  - Postgres persistence split out to **T-012**. T-011 ships an atomic in-memory store behind the
    `PortfolioRepository` protocol, with a reusable store contract suite that T-012 must pass.
  - Duplicate removal = explicit row exclusion (`PUT/DELETE /imports/{id}/rows/{n}/exclusion`), never
    aggregation. Two included rows on the same instrument block confirm.
  - Confirm needs `Idempotency-Key` + `preview_revision`. It does not re-resolve instruments.
  - The default store is seeded with the fixture version, so T-006 valuation of `…0100` keeps working.
- Contracts v1.1 bump kept out of T-011 (no schema change needed) and filed as **T-013**.
- Checked the spec's acceptance step 1 against the real preview code: rows 2/5 unresolved, rows 1/20
  share SYN01. The fixture `source_hash` matches `holdings.csv`.

## Tests run
- None (docs only).

## Contract changes proposed (not applied)
- Unchanged from the T-006 handoff; now tracked as T-013: `valuation.schema.json` (T-006 `cc8f1f5`),
  `issue.schema.json` + `brief.coverage.pending_sources` (T-007 `3e744e2`),
  `instrument.schema.json` / `symbol_mapping.schema.json` (T-005 `f0caae1`).

## Unresolved / assumptions
- T-011: tenant is a placeholder constant (the fixture tenant) until auth. `revision` increments on no-op
  row edits too. Blank rows are auto-excluded, not user-excluded.
- T-006 follow-up (for T-008): a `0` or negative close passes observation validation and is valued as
  a real price (a `0` close → market value `0.00`, counted as priced, weight `no_priced_value`).
  Provider adapters should reject non-positive closes.
- T-006: `Price.value` keeps the observation's original precision; an empty confirmed portfolio with
  USD cash has `total_value` = cash; repositories are process-lifetime synthetic snapshots until T-011.
- T-005 review nits (non-blocking): `domain/instruments.py` imports `InstrumentRepository` from
  `services/` (move into `domain/` by T-008); bare `assert` in resolver code; function-local
  `from datetime import UTC` in `routes/instruments.py`.
- T-005: display-symbol rule for several active aliases is labels-only; future-only mappings return
  `symbol_not_found`; master data is a process-lifetime snapshot; confirm does not re-resolve (settled in the T-011 spec).
- T-007: Today parses only UTC `Z` timestamps; stale = `cutoff` Friday / `published_at` Monday (confirm);
  Ajv runs with `strictTypes`/`strictRequired` off for if/then subschemas.
- Carried over: upload request-size limit before exposing `/imports`; previews are process-local;
  one handoff file per task would avoid merge conflicts here; JEV pricing outside the $25 model cap
  (ADR-003 Open); T-009 injection variant on usable data; consumers must enable date-time format
  checking (ADR-001 §3).
