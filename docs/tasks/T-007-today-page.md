# T-007 — Today page and evidence states (fixture-driven)

- **Implementer:** Claude Code   **Reviewer:** Codex
- **Branch:** task/T-007-today   **Depends on:** T-002, T-003 (merged)   **Contract version:** v1
- **Effort:** default

## Problem
Today is the product's front door, and its hardest part is being honest when data is incomplete.
There is no UI beyond a placeholder, and no pipeline yet produces briefs, so the states have to be
designed and proven against fixtures before the API exists.

## User-visible outcome
`/` shows the Today page for the synthetic portfolio. A fixture switcher, shown in development and
tests only, renders each shared state: `ready`, `running`, `partial`, `stale`, `failed`, and
`no_material_change`. Each state says plainly what was checked, what's missing, and when.

## Read (only these)
- `docs/product.md` — "Morning portfolio analysis", "UX principles", "Information architecture",
  "Surfaces" (Today and Shared state model bullets)
- `packages/contracts/schemas/brief.schema.json`, `decision.schema.json`, `evidence.schema.json`
- `evals/fixtures/portfolio/README.md`, `evals/fixtures/packets/10-failed-coverage/`
- `apps/web/AGENTS.md` (Next.js version notes), existing `apps/web/app/*`

## Owned paths (edit only these)
- `apps/web/app/` (page, layout, globals.css), `apps/web/components/`, `apps/web/lib/today/`
- `apps/web/fixtures/today/` (new), `apps/web/tests/`
- `apps/web/package.json` + `package-lock.json` (exact-pinned dev dependencies only)

## Inputs / outputs
**View model** (`apps/web/lib/today/types.ts`): `TodayView` = header (session, timezone, snapshot
time in exchange and local time, coverage checked/failed), `status` (the shared state enum), up to 3
`issues`, `upcoming_events`, optional `last_good_snapshot` (stale and failed only).
Each issue: holding (symbol + name), observation (a fact with source and time), interpretation
(labeled as interpretation), evidence status (`supported | partial | contested | insufficient`),
exposure (a precomputed value labeled "calculation", or "unavailable"), next research question, and
evidence items (source, published and known times, excerpt).

**Fixtures** (`apps/web/fixtures/today/<state>.json`, one per state): hand-authored, synthetic. The
`brief` part of each validates against `brief.schema.json`. Instrument ids exist in
`evals/fixtures/portfolio/positions.json`. `partial` reuses packet 10's failed source.

## Invariants
- The UI does no portfolio arithmetic; exposure comes precomputed or is shown as unavailable.
- Missing is shown as unavailable, never `0` or blank.
- `no_material_change` copy: "No new material changes found within current coverage." plus a
  "View monitored coverage" disclosure. Never shown when coverage is empty or a source failed.
- `stale` and `failed` never present the last good snapshot as current: it's separate and labeled
  with its time.
- No confidence percentages, trade verbs, urgency, flashing, or countdowns. Verbs: Investigate,
  Compare evidence. Warning color only with text and an icon. Tabular numerals.
- Facts, calculations, and interpretations are visually and textually distinct.

## Error states
All six shared states, plus an unreadable-fixture state showing "Today couldn't load", with no
financial content.

## Acceptance fixtures
- Vitest per state: the key copy, the heading structure, and the absence of forbidden content
  (`%` confidence, "buy"/"sell" as calls to action, a last-good snapshot styled as current).
- Vitest: every fixture's `brief` validates against the v1 schema (Ajv 2020 with formats); its
  instrument ids resolve against the portfolio fixture.
- Playwright: `ready` and `partial` render with no external requests; keyboard-only focus reaches
  every issue's disclosure; evidence expands and collapses.
- Mobile width (390 px): no horizontal scroll.

## Validation commands
```
make test
make lint
make test-e2e
```

## Planned commits (small and real; see AGENTS.md)
1. `feat:` TodayView types and the ready fixture
2. `test:` fixture schema and reference checks
3. `feat:` design tokens and base layout (header, coverage line)
4. `feat:` issue card with fact, calculation, and interpretation labeling
5. `feat:` evidence disclosure
6. `feat:` partial and failed states
7. `feat:` stale and running states with last-good snapshot
8. `feat:` no_material_change state with coverage disclosure
9. `test:` Playwright keyboard, disclosure, and mobile checks
10. `docs:` handoff and ledger

## Excluded scope
API calls (no `/briefs` endpoint yet) · stock detail and Investigate destination (the link goes to a
labeled placeholder) · Portfolio, Discover, and Plans pages · auth · real data · the `Issue` contract
(proposed in the handoff, not added to `packages/contracts`).

## Handoff checklist
- [ ] Validation commands pass
- [ ] `Issue` view-model contract proposal written in the handoff
- [ ] Branch pushed; `docs/handoffs/CURRENT.md` and the LEDGER row updated
