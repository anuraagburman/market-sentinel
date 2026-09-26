# Handoff — T-003 synthetic fixtures

- **Updated:** 2026-09-26 19:35 SGT by Codex
- **Branch / worktree:** task/T-003-fixtures @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews the latest T-003 commit addressing portfolio diversity, starting
with `evals/fixtures/generate.py` and `evals/tests/test_fixtures.py`.

## Done this session
- Addressed the single review request: varied quantities, total costs, and closing prices.
- Included fractional quantity 2.5, price 625.50, price 3.25, and a largest priced weight of 48.82%.
- Regenerated portfolio CSV/JSON and source hash; preserved all five import cases and all adversarial packets.
- Updated fixture checks for CSV/position consistency and valuation diversity; documented the edge cases.
- Ledger status remains ready_for_review for this revision.

## Tests run
- `make test` → pass: 134 Python tests + 1 Vitest test; existing Starlette deprecation warning.
- `make lint` → pass: Ruff, ESLint, Next route generation, TypeScript.
- Direct Ruff check and format check on changed evals Python files → pass.
- Generator replay → all 55 CSV/JSON files reproduced byte-for-byte.

## Contract changes proposed (not applied)
- none

## Unresolved / assumptions
- No new unresolved assumptions. CSV cost_basis remains total cost.
- Twenty raw rows resolve to nineteen positions; duplicate removed, missing cost stays null,
  and the missing-price position is excluded from priced-value concentration.
