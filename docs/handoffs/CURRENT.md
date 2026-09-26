# Handoff — T-007 Today page and evidence states

- **Updated:** 2026-09-27 by Claude Code
- **Branch / worktree:** task/T-007-today @ ~/code/ms-wt/web
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Codex re-reviews the session-name fix (commits 467dea6 test, 2ccd67f fix): `git diff 5a7cdda..task/T-007-today`.
Then run `make test`, `make lint`, `make test-e2e`. If it's clean, T-007 is ready to merge to `main` (`--no-ff`).

## Done this session
- **Review fix (P2, session name):** `SESSION_NAMES` is now a const tuple in `lib/today/types.ts`
  (`SessionName` is derived from it, like `SURFACE_STATUSES`). `parseToday` rejects any
  `header.session.name` not in it. `includes` ignores inherited keys, so `__proto__` and
  `constructor` are rejected.
- Five regression cases (missing, unknown, wrong type, `__proto__`, `constructor`). Each asserts that
  parsing fails and that TodayPage renders only "Today couldn't load", with no financial content.
- Checked the components for other lookups keyed by brief data. `SESSION_LABELS` was the only one.
  `status` and `evidence_status` were already enum-checked.
- Earlier on this branch: the malformed date/timezone fix (9ef7b98, dc210bd), which Codex confirmed.

## Tests run
- `make test` → pytest 134 passed; Vitest 64 passed (2 files)
- `make lint` → passed
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
