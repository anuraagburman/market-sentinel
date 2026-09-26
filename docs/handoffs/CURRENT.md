# Handoff — main after T-007 merge

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** main (merge built in ~/code/ms-wt/web, pushed to origin/main; `~/code/market-sentinel` still needs `git pull --ff-only`)
- **Status:** T-007 `merged`; T-005 `ready`

## Next step (exact — the next agent starts here)
- **Codex**, in a fresh session: in `~/code/ms-wt/api`, `git checkout -b task/T-005-instrument-resolution origin/main`
  and implement `docs/tasks/T-005-instrument-resolution.md`, starting with planned commit 1
  (synthetic instrument master in `evals/fixtures/generate.py`).
- Whoever next opens `~/code/market-sentinel`: `git pull --ff-only` first. The local `main` there is behind origin.

## Done this session
- Merged `task/T-007-today` into `main` with `--no-ff`, after Codex's clean re-review of `5a7cdda..task/T-007-today`.
  `/` now renders the Today page from fixtures (`apps/web/fixtures/today/`), with every shared state plus
  "Today couldn't load".
- Before merging, the review fixes were: validate timestamps, session date, and IANA timezones at the
  boundary; validate `session.name` against the enum, including prototype keys.
- The only merge conflict was this file. It now merges both handoffs.

## Tests run
- On the merge result: `make test` → pytest 210 passed, Vitest 64 passed; `make lint` passed;
  `make test-e2e` → 9 passed (Chromium).

## Contract changes proposed (not applied)
- **`issue.schema.json` (v1.1 candidate)**, from T-007 and mirroring `Issue` in `apps/web/lib/today/types.ts`:
  `id`, `decision_id` (uuid), `holding {instrument_id, symbol, name}`, `observation {text, source, observed_at}`,
  `interpretation`, `evidence_status` (`supported | partial | contested | insufficient`),
  `exposure` = `{kind: "calculation", value, basis}` | `{kind: "unavailable", reason}` (value from T-006
  valuation, never a model), `next_question`, `evidence_ids` (the API resolves them to items with `source`,
  `published_at`, `known_at`, `excerpt | null`). A brief would carry `issues` (max 3) alongside `decision_ids`.
- Add `pending_sources` to `brief.coverage` for `running` (the view has it, the contract doesn't).
- T-005 will propose `instrument` and `symbol_mapping` schemas; bundle all of these into one v1.1 bump.

## Unresolved / assumptions
- T-007: the Today page parses only UTC `Z` timestamps. Relax this if the /briefs API emits offsets.
- T-007 stale fixture: `cutoff` = Friday (newest complete data), `published_at` = Monday. Confirm this
  meaning of stale. `last_good_snapshot` appears only on stale and failed; running shows no prior results.
- T-007: Ajv runs with `strictTypes`/`strictRequired` off for the contract's if/then subschemas.
- T-005 changes the `resolution` field shape in the import preview API (string → object). Nothing
  consumes it yet. `as_of` = UTC date of `received_at`; whether confirm re-resolves is open.
- The default instrument repository reads `evals/fixtures/instruments/` until T-008.
- Carried over: an upload request-size limit is needed before exposing `/imports`; previews are process-local;
  consider one handoff file per task (T-007 conflicted on this file as predicted); horizon enum (T-000);
  JEV access (blocks T-009); T-009 injection variant on usable data; consumers must enable date-time
  format checking (ADR-001 §3).
