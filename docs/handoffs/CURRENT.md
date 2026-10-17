# Handoff — T-014 policy engine v1 + decision envelope: spec ready

- **Updated:** 2026-10-17 by Claude Code
- **Branch / worktree:** task/T-014-policy-envelope (spec only, branched from main `9a9eb1c`)
- **Status:** ready. Implementation is blocked on the T-009 merge, because it builds on `app/judgment/`.

## Next step (exact — the next agent starts here)
1. **Codex** (when T-008 reaches a stopping point): review T-009 with
   `git diff origin/main...origin/task/T-009-jev-decisions`. The brief is in that branch's
   `docs/handoffs/CURRENT.md`.
2. **Claude Code:** fix any T-009 findings, then merge T-009 with `--no-ff`. Then, in `~/code/ms-wt/web`:
   `git switch task/T-014-policy-envelope && git merge origin/main`, and start T-014 with a failing
   test for the `split_unadjusted` gate (packet 02).

## Done this session
- Anuraag decided (2026-10-17) that evidence-only packets with no observations (03, 10) are **partial,
  not unusable**. The spec encodes this as a deterministic `no_observations` → `partial` cap.
- Wrote `docs/tasks/T-014-policy-envelope.md`, including:
  - Gates: split, no-observations, critical-source-missing, stale, timestamp order.
  - Exposure, grounded in stage 3.
  - A deterministic action table, with provisional priority weights.
  - Envelope assembly with an idempotent `decision_id`.
- Found while writing the spec: packet 07 is unusable only because of its declared coverage gap. No
  current code reads `coverage_gaps`, so T-014 adds the `critical_source_missing` gate.

## Tests run
- None. This is a docs-only change.

## Contract changes proposed (not applied)
- v1.2: typed coverage-gap codes, for example `{code: "required_observations_missing", detail}`, instead of
  free text, so the critical-gap gate stops treating every gap as critical.

## Unresolved / assumptions
- The priority weights and thresholds will be provisional placeholders until T-010 fits them.
- `expected_session_close` is a caller parameter until T-008 lands an exchange calendar.
- The stage-3 re-recording (adding exposure to the state) needs Anuraag's approval for about $0.001 of
  live JEV.
- The carry-forwards from the main handoff (the T-012 store follow-ups, T-008's non-positive close)
  are unchanged.
