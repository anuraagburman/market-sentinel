# Handoff — T-007 Today page and evidence states

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** task/T-007-today @ ~/code/ms-wt/web
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Codex re-reviews T-007, starting with the P2 fix (commits 9ef7b98 test, dc210bd fix):
`git diff 515313e..task/T-007-today`, then the full `git diff main...task/T-007-today` against
`docs/tasks/T-007-today-page.md`. Run `make test`, `make lint`, `make test-e2e`.

**Review fix (P2, malformed dates/timezones):** `parseToday` in `apps/web/lib/today/load.ts` now rejects:
- any timestamp that isn't a UTC ISO string ending in `Z` with a real calendar date and time:
  `header.snapshot_at`, `observation.observed_at`, evidence `published_at`/`known_at`,
  `upcoming_events[].at`, `last_good_snapshot.snapshot_at`, and the nested last-good issues;
- a `session.date` that isn't a real `YYYY-MM-DD` date (so `2026-02-30` is rejected);
- a `user_timezone`/`exchange_timezone` that `Intl.DateTimeFormat` rejects.
Each rejected value renders "Today couldn't load". There are 13 new Vitest cases, one per field or variant.
Offsets like `+00:00` are rejected on purpose, because the view model says times are UTC. Relax the
check if the /briefs API emits offsets.

## Done this session
- `/` renders Today from hand-authored fixtures (`apps/web/fixtures/today/<state>.json`, one per shared
  state, plus `unreadable.json`). In non-production builds a fixture switcher is available at `/?state=<name>`.
- The view model is in `apps/web/lib/today/types.ts`. `lib/today/load.ts` shape-checks fixtures at the
  boundary, and anything malformed renders only "Today couldn't load".
- Issue cards label Fact (with source and time), Calculation (precomputed exposure, or "Exposure
  unavailable"), and Interpretation in text. The evidence disclosure uses native `<details>` and shows
  published and known-to-us times and an excerpt only where licensed.
- States: partial names the failed source; failed and stale show retry and put the last complete brief
  in a separate, dated "not current" section; running lists checked and pending sources;
  no_material_change shows the required copy and "View monitored coverage", and is replaced by
  "Coverage incomplete" if coverage is empty or a source failed.
- Investigate links go to a labeled placeholder at `/investigate`.
- Added exact-pinned dev dependencies `ajv@8.20.0` and `ajv-formats@3.0.1`.

## Tests run
- `make test` → pytest 134 passed; Vitest 59 passed (2 files)
- `make lint` → Ruff clean; ESLint + typegen + tsc clean
- `make test-e2e` → 9 passed (Chromium)

## Contract changes proposed (not applied)
- **`issue.schema.json` (v1.1 candidate)**, mirroring `Issue` in `apps/web/lib/today/types.ts`:
  `id`, `decision_id` (uuid, links the decision envelope), `holding {instrument_id, symbol, name}`,
  `observation {text, source, observed_at}` (fact), `interpretation` (string),
  `evidence_status` (`supported | partial | contested | insufficient`),
  `exposure` = `{kind: "calculation", value, basis}` | `{kind: "unavailable", reason}` (value is
  produced by T-006 valuation, never by a model), `next_question`, and `evidence_ids` (the API resolves
  them to evidence items with `source`, `published_at`, `known_at`, and `excerpt | null`).
  A brief would carry `issues` (max 3) alongside `decision_ids`.
- Consider adding `pending_sources` to `brief.coverage` for `running`. The view has it, but the
  contract doesn't.

## Unresolved / assumptions
- The exposure strings in the fixtures were computed deterministically (Python `Decimal`) from the
  portfolio fixture: 18 of 19 holdings priced, SYN01 48.8%, SYN12 6.1%, SYN10 3.1%. The UI only displays them.
- In the stale fixture, the brief `cutoff` is Friday's (the newest complete data) and `published_at` is
  Monday. The header says "Data as of" Friday and the notice explains. Confirm this is the intended
  meaning of stale.
- `last_good_snapshot` appears only on stale and failed (per the view model). Running shows no prior
  results. The planned-commit list suggested running might show them.
- Vitest's include is `tests/**/*.test.tsx` (vitest.config.ts is outside owned paths), so the node-only
  fixture test keeps a `.tsx` suffix and uses `// @vitest-environment node`.
- Ajv runs with `strictTypes`/`strictRequired` off: the contract's if/then subschemas are valid 2020-12
  but trip Ajv's extra strictness. Unknown keywords still fail.
- Carried from main: T-009 injection variant on usable data; one handoff file per task to avoid
  CURRENT.md/LEDGER.md conflicts between parallel branches; horizon enum and JEV access (T-000).
