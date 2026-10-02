# Handoff — T-013 contracts v1.1 ready for review; T-012 still with Codex

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** task/T-013-contracts-v1-1 @ ~/code/ms-wt/web
- **Status:** T-013 ready_for_review · T-012 unchanged by this session (Codex, `task/T-012-postgres-store`)

## Next step (exact — the next agent starts here)
- **Codex — T-013 review.** Review `git diff origin/main...origin/task/T-013-contracts-v1-1` against
  `docs/tasks/T-013-contracts-v1-1.md` and `docs/decisions/ADR-004-contracts-v1-1.md`. Check that each schema
  fits its producer (`apps/api/app/models/valuation.py`, `models/instruments.py`) and that the additive rule
  (ADR-004 §1) holds. Then run the validation commands in the task file.
- **Codex — T-012.** Continue as specified in `docs/tasks/T-012-postgres-store.md`. T-013 touches no T-012 path.
  It adds only the new file `apps/api/tests/test_contracts_v1_1.py`.

## Done this session
- Wrote the T-013 spec. Ledger: T-013 → `review`.
- Added 4 new schemas: `valuation`, `issue`, `instrument` and `symbol_mapping`.
- Added `common` defs: `date`, `money_string`, `weight_string`, `unavailable_reason`, `unavailable`, `amount`
  and `weight_amount`.
- Added optional `issues` (at most 3) and `coverage.pending_sources` to the brief.
  - New rule: nonempty `pending_sources` ⇒ `running`.
  - New rule: `no_material_change` carries no issues.
- Wrote ADR-004. It covers the additive rule, the tagged calculation/unavailable shape, Issue exposure as the
  T-006 weight, and the OpenAPI-only scope for confirm/readiness.
- Examples went from 13 valid / 31 invalid to 23 valid / 69 invalid.
  - I printed why each new invalid case is rejected; each fails on its intended rule.
  - The v1 examples are unchanged and still pass.
- `apps/api/tests/test_contracts_v1_1.py` validates the real valuation response, the empty-portfolio and
  unknown-cash valuation, and every loaded instrument and mapping, with format checking on.
  - A mutation check (temporarily requiring 3-place money) made it fail, so it catches drift.
- The Today `running.json` brief now carries `pending_sources`, and the fixture test pins it to the view's
  `pending` ids.

## Tests run
- `make test` → 375 pytest passed; Vitest 64 passed (2 files).
- `make lint` → exit 0.
- `python3 packages/contracts/tests/gen_examples.py && git diff --exit-code packages/contracts/tests/examples`
  → clean.
- `make contracts && git diff --exit-code packages/contracts/openapi.json` → clean (no OpenAPI change).
- `git diff --check` → clean.

## Contract changes proposed (not applied)
- none (v1.1 is applied on this branch, pending review).

## Unresolved / assumptions
- `price.value` must be a positive decimal. A zero or non-positive close now violates the contract. This is
  consistent with the T-008 note, but the valuation domain doesn't reject such a close yet.
- `symbol_mapping.symbol` rejects ASCII lowercase and leading or trailing whitespace. It allows other
  characters (`BRK.B`), matching `FileInstrumentRepository`.
- Issue `id` is a UUID. The T-007 view fixtures use slug ids (`issue-syn01-outlook`), which is fine because
  the view isn't the contract. When the /briefs web task puts `issues` into the fixture briefs, the view
  needs a weight→text formatter and a reason-code→text mapping.
- Deferred to later work:
  - Whether every issue `decision_id` appears in the brief's `decision_ids`. The publish verifier must check
    this.
  - Codegen.
- Carried over:
  - Web lane: group `row_has_errors` and `row_unresolved` per row in the import UI.
  - Provider adapters should reject non-positive closes (T-008).
  - T-005 nits: `domain/instruments.py` imports from `services/`; a bare `assert`; a local `UTC` import.
  - Add an upload request-size limit before exposing `/imports`.
  - JEV pricing sits outside the $25 model cap (ADR-003 Open).
  - T-009 injection variant on usable data.
  - Consumers must enable date-time format checking (ADR-001 §3).
  - Today parses only UTC `Z` timestamps.
