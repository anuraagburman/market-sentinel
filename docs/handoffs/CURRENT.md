# Handoff — T-015 integration complete

- **Updated:** 2026-10-18 by Codex
- **Branch / worktree:** main @ ~/code/market-sentinel (integration); review/T-015-provisional-labels @ ~/code/ms-wt/api
- **Status:** merged

## Next step (exact — the next agent starts here)
Claude Code writes the T-010 spec, carrying forward the provisional-label limitations and
unresolved items below. T-010 remains backlog until that spec is reviewed and ready.

## Done this session
- Confirmed the task branch already contained review documentation `7c37d32`.
- Reviewed follow-up `56c79e4`, which rejects label values with the wrong type.
- Integrated the approved T-015 history into main with `--no-ff` and pushed main.
- Updated the task review record and ledger to merged. No label or contract changes.

## Tests run
- `make test` → 608 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed.
- `make lint` → passed (Ruff, formatting, ESLint, Next type generation, TypeScript).
- `git diff main...HEAD --check` → passed before integration.
- Sandbox cache access initially blocked tests; approved rerun passed.

## Contract changes proposed (not applied)
- None. Carry forward typed coverage-gap codes (v1.2) and the optional interpretation_conflict Noul proposal.
- Proposed `TODO(label)` example text for `decisions/taxonomy/v1.yaml` (taxonomy owner decides):
  - data_usability positive: "two fresh regular-session closes, no coverage gaps (04) -> usable"
  - data_usability negative: "2-for-1 split with unadjusted 100.00 -> 50.00 closes (02) -> unusable"
  - event_family positive: "device approval with event_type regulatory (04) -> regulatory"
  - primary_context negative: "approval news, no benchmark moves (04) -> unknown, not company"
  - novelty positive: "correction_of an earlier revenue report (09) -> update"
  - novelty negative: "ten syndicated copies of one wire story (03) -> repeated"
  - evidence_sufficiency negative: "'miss' headline, no consensus figure (01) -> insufficient"
  - research_relevance positive: "verified approval on a holding, materiality unconfirmed (04) -> 4"
  - research_relevance negative: "price-feed outage on a holding, no event (05) -> 2"
  - interpretation_conflict positive: "company release says October, supplier says December (06) -> yes"

## Unresolved / assumptions
- No discrimination signal on primary_context (all unknown) or thesis_impact (all abstain), and
  interpretation_conflict has n=1. T-010 should report these as abstention and refusal-to-guess
  checks only. A packet with benchmark moves, a recorded thesis and a completed counterevidence search
  would fix this, as a separate fixture task.
- "Verified" in research_relevance means a non-contested company fact claim in the packet; no
  packet has independent verification.
- Carry forward from T-014: runtime dependency promotion (pyyaml, jsonschema/referencing), raw-output storage,
  excluded-claim audit ids, billing-status verification, usable-packet injection probe, T-010 relevance
  calibration, T-012 follow-ups, T-008 non-positive close and exchange calendar.
