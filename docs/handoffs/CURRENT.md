# Handoff — main after T-005 merge

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** main (merge built in ~/code/ms-wt/web, pushed to origin/main; `~/code/ms-wt/api`
  and `~/code/market-sentinel` need `git pull --ff-only` / a fresh branch from `origin/main`)
- **Status:** T-005 `merged`; T-006 `backlog` (spec not written yet)

## Next step (exact — the next agent starts here)
1. **Anuraag** answers the T-000 scope and cost questions (universe, horizons, currency handling,
   briefing time/timezone, spend ceiling, data rights). Claude Code has the question list.
2. **Claude Code** records the answers as `docs/decisions/ADR-002-scope-and-schedule.md` and
   `ADR-003-cost-and-data-rights.md`, then writes `docs/tasks/T-006-portfolio-valuation.md` and
   moves T-006 to `ready`. Valuation depends on the currency answer: the fixture master already
   contains a CAD instrument (Synthela 21), so the spec must say whether FX is valued or flagged.
3. **Codex**, once T-006 is `ready`: in `~/code/ms-wt/api`, `git checkout -b task/T-006-valuation origin/main`
   and implement from the spec's planned commit 1.

## Done this session
- Reviewed `origin/main...task/T-005-instrument-resolution` (@ `f0caae1`) against the task file.
  No blocking findings. The branch was already at the user-approved alias rule.
- Merged with `--no-ff`. Amended the T-005 task file so it allows simultaneous symbol aliases and
  rejects overlaps only for the same instrument and symbol, matching the code and fixtures.

## Tests run
- On the T-005 branch head: `make test` → pytest 243 passed, Vitest 64 passed; `make lint` passed;
  fixture regeneration and `make contracts` both byte-identical.
- Startup fail-fast checked by hand: overriding the instrument repository with a raising loader
  makes `TestClient(app)` raise before serving.
- On the merge result: `make test` → 243 + 64 passed; `make lint` passed.

## Contract changes proposed (not applied)
- One v1.1 bump should bundle: T-007's `issue.schema.json` and `brief.coverage.pending_sources`,
  and T-005's `instrument.schema.json` / `symbol_mapping.schema.json` (full shapes are in the T-005 handoff,
  commit `f0caae1`, and T-007 handoff, commit `3e744e2`). Best landed before or with T-006 so valuation
  builds on final shapes.

## Unresolved / assumptions
- T-005 review nits (non-blocking, fix opportunistically): `domain/instruments.py` imports the
  `InstrumentRepository` protocol from `services/` (move it into `domain/` by T-008); bare `assert`
  in production resolver code; function-local `from datetime import UTC` in `routes/instruments.py`.
- T-005: display symbol with several active aliases uses a least-shared-then-lexical rule (labels only);
  provider data should define primary symbols. Future-only mappings return `symbol_not_found`.
  Master data is a process-lifetime snapshot; whether confirm re-resolves is open.
- T-007: Today parses only UTC `Z` timestamps; stale = `cutoff` Friday / `published_at` Monday (confirm);
  Ajv runs with `strictTypes`/`strictRequired` off for if/then subschemas.
- Carried over: upload request-size limit before exposing `/imports`; previews are process-local;
  one handoff file per task would avoid merge conflicts here; JEV access blocks T-009; T-009 injection
  variant on usable data; consumers must enable date-time format checking (ADR-001 §3).
