# Handoff — T-005 Instrument resolution

- **Updated:** 2026-09-27 by Codex
- **Branch / worktree:** task/T-005-instrument-resolution @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews `git diff origin/main...task/T-005-instrument-resolution` against
`docs/tasks/T-005-instrument-resolution.md`, applying the user-approved alias rule below,
then runs `make test`, `make lint`, and the fixture/contract regeneration checks.

## Done this session
- Created the requested task branch from `origin/main`. Implemented planned commits 1–6 separately,
  including a failing resolver-test commit followed by the passing implementation.
- Added deterministic synthetic instruments and effective-dated mappings. Existing portfolio and
  packet files regenerate byte-identically. Fixture checks cover shapes, entity UUID uniqueness,
  foreign keys, dates, share classes, ticker changes, reuse, and ambiguity.
- Added a pure resolver and an injectable `InstrumentRepository` protocol with a validated,
  file-backed synthetic default. Invalid master data fails startup before requests are served.
- Preview rows now expose resolved / ambiguous / unresolved / not_attempted objects. Receipt time
  comes from an injectable clock, is normalized to UTC, and determines the resolution date.
  Validation status stays separate; summaries include `by_resolution`.
- Added exact `GET /instruments` lookup and select/clear row-resolution endpoints. Selections keep
  automatic candidates and non-currency issues, recompute currency warnings, preserve raw/parsed
  data, and update counts. Clearing restores automatic resolution on the original preview date.
- Regenerated OpenAPI without changing shared JSON schemas. The internal CSV parser still emits
  its pending placeholder; the service replaces it before creating the public preview model.
- Updated the obsolete pending-resolution assertion in `test_imports_api.py` with explicit user
  authorization to edit that otherwise unowned file.

## Tests run
- `uv run --project apps/api --locked pytest evals/tests/test_fixtures.py` → 71 passed.
- Resolver specification before implementation → expected missing-module collection failure.
- Resolver + loader targeted checks → 12 passed; import integration → 79 passed;
  lookup/startup checks → 4 passed; select/clear checks → 11 passed.
- `make test` → 243 Python tests and 64 Vitest tests passed.
- `make lint` → Ruff check/format, ESLint, Next typegen, and TypeScript passed.
- `python3 evals/fixtures/generate.py && git diff --exit-code evals/fixtures` → passed.
- `make contracts && git diff --exit-code packages/contracts` → passed.
- `git diff --check origin/main...HEAD` → passed.
- One upstream Starlette/AnyIO deprecation warning; no test failures.

## Contract changes proposed (not applied)
For the next shared schema version bump alongside the earlier T-007 Issue proposal:
- `instrument.schema.json`: object, no extra properties; required `id` (UUID string), `name`
  (nonempty string), `asset_type` (`common_stock | preferred_stock`), `currency` (three uppercase
  ASCII letters). Identity is the UUID, never the symbol.
- `symbol_mapping.schema.json`: object, no extra properties; required `symbol` (nonempty,
  trimmed, ASCII-uppercased string), `instrument_id` (UUID), `valid_from` (date, inclusive),
  `valid_to` (date or null, exclusive/open). Repository validation enforces foreign keys,
  `valid_to > valid_from`, and no interval overlap for the same instrument AND symbol.
  Different symbols may alias one instrument; one symbol may overlap across instruments.
- Cross-record referential and interval validation remains application-level. No shared JSON
  schema edits were made by this task; API shapes are in generated OpenAPI.

## Unresolved / assumptions
- User explicitly resolved the task contradiction: **allow simultaneous aliases; reject overlaps
  for the same instrument and symbol**. This permits SYN02/SYN02P alongside SYN-AMB. The task file's
  stronger one-symbol-per-instrument wording was left unchanged because it is outside owned paths.
- With multiple active aliases, display prefers the alias shared by the fewest active instruments,
  then lexical order. This gives SYN02 and SYN02P for ambiguous candidates. This ordering affects
  labels only and never selects an identity. Future provider data should define primary symbols.
- A symbol with only future mappings returns `symbol_not_found` with a date-specific message;
  there is no task-defined separate future-listing code.
- Master data is an immutable process-lifetime snapshot. Clear/reselect recomputes automatic
  results from that same snapshot. Durable master versioning and preview persistence remain future work.
- Small CSV boundary/error inputs are inline test bytes, avoiding edits to the existing fixture
  directory outside the owned-path list. All tests remain offline and deterministic.
- Scope remains research/import previews only: no confirmation, valuation, provider calls, or orders.
