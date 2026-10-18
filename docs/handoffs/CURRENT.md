# Handoff — T-015 provisional labels: ready for review

- **Updated:** 2026-10-18 by Claude Code
- **Branch / worktree:** task/T-015-provisional-labels @ ~/code/ms-wt/web
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Codex, in `~/code/ms-wt/api` (the web worktree has this branch checked out, so review it on a
`review/T-015-provisional-labels` branch): review `git diff main...task/T-015-provisional-labels`
against `docs/tasks/T-015-provisional-labels.md`. Check each `why` against its packet. Do **not** open
`evals/recordings/` while reviewing labels. Afterwards, Claude Code writes the T-010 spec.

## Done this session
- `test_labels.py` (written first): checks the decision id set, that values are in `outputs`, that
  abstentions are in `abstain_when` (or are `unusable_input` downstream of unusable), agreement with
  `expected.json`, that `research_action` appears exactly when a hard gate forces it, the packet_hash
  tie, and the provisional/labeler fields.
- `evals/labels/v1/*.json`: 10 label files, drafted blind and **approved by Anuraag in chat on
  2026-10-18**, all 10 as drafted.
- `evals/labels/README.md`: the procedure, the rubric (four rules Anuraag decided: counterevidence
  search counts as incomplete; novelty defaults to unclear; primary_context is unknown everywhere;
  a single close is partial) and the per-decision counts for T-010.
- Also: the earlier T-014 next step was already done. It merged to main as `265eef7`.

## Tests run
- `uv run pytest evals/tests/test_labels.py` → 11 passed. Two mutation checks failed as expected
  (dropping a gate action; a value outside `outputs`).
- `make test` → 608 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed.
- `make lint` → passed.

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
