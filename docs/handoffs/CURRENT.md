# Handoff — T-015 provisional labels: ready (spec written)

- **Updated:** 2026-10-18 by Claude Code
- **Branch / worktree:** main (spec only); implementation goes on `task/T-015-provisional-labels` in `~/code/ms-wt/web`
- **Status:** ready

## Next step (exact — the next agent starts here)
Claude Code, fresh session in `~/code/ms-wt/web`: create branch `task/T-015-provisional-labels` from
`main` and follow `docs/tasks/T-015-provisional-labels.md`. Write `test_labels.py` first, then draft
labels packet by packet **without reading `evals/recordings/`**, and get Anuraag's approval on each
label in chat.

## Why T-015 before T-010 (Anuraag's decisions, 2026-10-18)
- `expected.json` labels only data_usability (5), research_action (2), exclusions (2) and freshness (1).
  Six of the eight taxonomy decisions have no labels, so T-010 has almost nothing to score. Labels
  are split into their own task, so the harness author isn't the one labeling the data it is scored on.
- **Persona baseline for T-010:** Claude Haiku (`claude-haiku-5-5`). One plain experienced-trader prompt
  over the same packets and questions, recorded once and then replayed offline like the JEV recordings.
  About 30 calls, under $0.10. Needs an Anthropic API key, and Anuraag approves the live run.
- **T-010 report scope:** preliminary and descriptive. Covers per-decision agreement, confusion tables,
  abstention coverage and policy-bypass checks, with n=10 and every metric marked provisional. No Brier,
  log-loss or calibration claims.
- Write the T-010 spec once T-015 is merged.

## Tests run
- None. This change is docs only.

## Contract changes proposed (not applied)
- None. Carry forward typed coverage-gap codes (v1.2) and the optional interpretation_conflict Noul proposal.

## Unresolved / assumptions
- No fixture packet has a recorded thesis, so `thesis_impact` is expected to abstain (`no_recorded_thesis`)
  on all 10. T-010 therefore has no thesis_impact signal. A thesis packet would be a separate task.
- Carry forward from T-014: runtime dependency promotion (pyyaml, jsonschema/referencing), raw-output storage,
  excluded-claim audit ids, billing-status verification, usable-packet injection probe, T-010 relevance
  calibration, T-012 follow-ups, T-008 non-positive close and exchange calendar.
