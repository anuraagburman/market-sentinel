# Handoff — T-007 Today page and evidence states

- **Updated:** 2026-09-27 by Codex
- **Branch / worktree:** task/T-007-today @ ~/code/ms-wt/web
- **Status:** changes_requested

## Next step (exact — the next agent starts here)
Fix the remaining P2 boundary-validation finding in `apps/web/lib/today/load.ts:71`, test-first:
validate `header.session.name` against `pre_market | regular | after_hours | closed`.
Missing or unknown names currently pass `parseToday` and render a blank session label.
With `name: "__proto__"`, parsing also succeeds, but `TodayHeader` looks up an inherited object
in `SESSION_LABELS` and React throws "Objects are not valid as a React child" instead of showing
"Today couldn't load". Reproduced by cloning ready.json, changing only session.name, parsing,
and rendering TodayPage with React DOM server.
Add regression cases for missing, unknown, wrong-type, and prototype-key names; verify the
fallback renders without financial content. Then rerun `make test`, `make lint`, `make test-e2e`
and return to Codex for re-review.

## Done this session
- Reviewed `515313e..task/T-007-today`, then the full `main...task/T-007-today` against T-007.
- The previous malformed-date/timezone crash is fixed; the 13 new boundary cases pass.
- Found and reproduced the unchecked session-name crash described above (P2).
- No application behavior changed during review; updated handoff and ledger only.

## Tests run
- `make test` → pytest 134 passed; Vitest 59 passed (2 files).
- `make lint` → Ruff, ESLint, Next typegen, and TypeScript passed.
- `make test-e2e` → 9 passed (Chromium).
- Read-only malformed-session reproduction → parseToday returned ok; React render threw.
- Initial sandbox runs could not access the uv cache or bind the dev server; all required
  commands passed when rerun with approved access.

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
