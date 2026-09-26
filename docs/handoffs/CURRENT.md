# Handoff — T-002 Core schemas and decision envelope

- **Updated:** 2026-09-26 by Claude Code
- **Branch / worktree:** task/T-002-schemas @ ~/code/ms-wt/web
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Codex: review `git diff main...task/T-002-schemas` against `docs/tasks/T-002*.md`. Reproduce with
`.venv/bin/python packages/contracts/tests/gen_examples.py && .venv/bin/python -m pytest packages/contracts/tests -q`
(deps in `packages/contracts/tests/requirements.txt`). Record verdict here as `changes_requested` or `ready_to_merge`.

## Done this session
- `packages/contracts/schemas/`: common + 10 entity schemas (PortfolioVersion, Position, Observation,
  Evidence, Claim, Event, Decision envelope, Brief, Plan, Run) with `if/then` invariants.
- `decisions/taxonomy/v1.yaml` (8 decisions, full design records, staging), `decisions/policies/v1.yaml` skeleton.
- `packages/contracts/tests/`: `gen_examples.py` (10 valid + 31 targeted invalid cases), `test_schemas.py`
  (schema validity, valid/invalid examples, taxonomy↔envelope lock, design-record completeness,
  no confidence/probability fields), `requirements.txt`.
- `docs/decisions/ADR-001-contracts-v1.md`.
- Fixed: two YAML scalars in `decisions/taxonomy/v1.yaml` began with `"` and broke parsing; now single-quoted.
- Fixed: pytest parametrize deprecation (generators wrapped in `list()`).

## Tests run
- `.venv/bin/python -m pytest packages/contracts/tests -q` → 56 passed, 0 warnings

## Contract changes proposed (not applied)
- none

## Unresolved / assumptions
- Horizon enum is `swing | multiweek` only (intraday excluded) — confirm in T-000.
- Evidence/Claim ids are free strings; entity ids are UUIDs.
- Cross-document checks (cutoff satisfaction, claim-id resolution) deferred to the API verifier.
- T-001 should wire `packages/contracts/tests` into `make test` and adopt `requirements.txt` into uv.
- JEV (TypeSafe) access unconfirmed; T-009 blocked on it.
