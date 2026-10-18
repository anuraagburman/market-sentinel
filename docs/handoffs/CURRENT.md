# Handoff — T-015 provisional labels: approved

- **Updated:** 2026-10-18 by Codex
- **Branch / worktree:** review/T-015-provisional-labels @ ~/code/ms-wt/api
- **Status:** ready_to_merge

## Next step (exact — the next agent starts here)
Integrate this review documentation into task/T-015-provisional-labels, then merge T-015 to main
with `--no-ff` and push main from the integration worktree. Codex approves implementation tip
`cf1eb26`. Afterwards, Claude Code writes the T-010 spec.

## Done this session
- Reviewed `git diff main...task/T-015-provisional-labels` against the task and taxonomy.
  Checked all 10 label files and each rationale against packet event, evidence, claims,
  observations and expected metadata (including packet 10's brief). No blocking findings.
- Confirmed cutoff/correction exclusions on 08/09, downstream abstentions on 02/07,
  hard-gate actions on 01/02/05/07, and README denominators and approved rubric.
- Did not open recordings or run policy-engine outputs to judge labels. Approval is a
  consistency review of Anuraag's approved provisional labels, not a second independent labeling.
- No implementation, label, fixture, taxonomy or contract changes. No merge performed here;
  the implementation branch remains checked out in the web worktree.

## Tests run
- `uv run pytest ../../evals/tests/test_labels.py ../../evals/tests/test_fixtures.py -q`
  (from apps/api) → 82 passed.
- `make test` → 608 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed.
- `make lint` → passed (Ruff, formatting, ESLint, Next type generation, TypeScript).
- `git diff main...HEAD --check` → passed.
- Initial targeted test run could not access the uv cache; approved rerun passed.

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
