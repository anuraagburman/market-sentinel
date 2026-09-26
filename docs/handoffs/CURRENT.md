# Handoff — T-003 synthetic fixtures

- **Updated:** 2026-09-27 03:30 SGT by Codex
- **Branch / worktree:** task/T-003-fixtures @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews T-003 implementation commit `d22b41b`, starting with
`evals/fixtures/README.md` and `evals/tests/test_fixtures.py`; run `make test` and
`make lint`. T-007 can consume these fixtures once T-003 lands.

## Done this session
- Added deterministic generator, 20-row synthetic CSV, confirmed portfolio, and ten adversarial packets.
- Added schema validation with date-time checking, cross-document references, hash checks,
  scenario assertions, policy hard-gate consistency, and invalid clean-brief checks.
- Wired contracts and fixture suites into make test; added four locked dev dependencies.
- Implementation committed as `d22b41b`; ledger set to ready_for_review.

## Tests run
- `make test` → pass: 133 Python tests + 1 Vitest test (one existing Starlette deprecation warning).
- `make lint` → pass: Ruff, ESLint, Next route generation, TypeScript.
- Direct Ruff check/format on new evals Python files → pass.
- Generator replay → all 55 CSV/JSON files reproduced byte-for-byte.

## Contract changes proposed (not applied)
- none

## Unresolved / assumptions
- Twenty raw rows resolve to nineteen positions: accidental duplicate is removed, not aggregated.
  Documented all five import resolutions in portfolio/README.md; T-004 owns the final CSV interface.
- expected.json is fixture metadata with a local strict schema, not a v1 decision envelope or JEV labels.
  Entity arrays validate element by element against v1 schemas.
- Packet 05 explicitly supplies a stale case; no production freshness threshold or policy engine added.
- Excluded evidence remains in packet hashes for audit; consumers must exclude dependent claims too.
