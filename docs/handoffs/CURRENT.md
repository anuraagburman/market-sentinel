# Handoff — T-002 Core schemas and decision envelope

- **Updated:** 2026-09-26 by Claude Code
- **Branch / worktree:** task/T-002-schemas @ ~/code/ms-wt/web
- **Status:** ready_for_review (re-review after changes_requested)

## Next step (exact — the next agent starts here)
Codex: re-review the fix commit only (`git show HEAD` on task/T-002-schemas) against your three findings. Reproduce with
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
- Codex review round 1 (changes requested), all three addressed:
  - P1 `brief`: `no_material_change` now requires ≥1 `checked_sources`.
  - P2 `utc_timestamp`: added `format: date-time`; tests enable format checking; `rfc3339-validator`
    added to requirements; `test_date_time_format_is_enforced` fails if the checker is missing.
  - P2 `decision`: `evidence_sufficiency: insufficient` ⇒ `insufficient_evidence`. The `if` requires the
    key, so an absent judgment doesn't trigger the gate (covered by a valid example).
  - New cases: 4 invalid (verified to fail on the old schemas) + 3 valid counterparts. ADR-001 updated.

## Tests run
- `.venv/bin/python -m pytest packages/contracts/tests -q` → 64 passed, 0 warnings
- Same suite against the pre-fix schemas → exactly the 4 new invalid cases fail

## Contract changes proposed (not applied)
- none

## Unresolved / assumptions
- Horizon enum is `swing | multiweek` only (intraday excluded) — confirm in T-000.
- Evidence/Claim ids are free strings; entity ids are UUIDs.
- Cross-document checks (cutoff satisfaction, claim-id resolution) deferred to the API verifier.
- Consumers (API/Pydantic, web) must enable date-time format checking; recorded in ADR-001 §3.
- `unpriced_instrument_ids` doesn't block `no_material_change` (quiet-day copy says "within current
  coverage"). Revisit if T-007 shows it misleads.
- T-001 should wire `packages/contracts/tests` into `make test` and adopt `requirements.txt` into uv.
- JEV (TypeSafe) access unconfirmed; T-009 blocked on it.
