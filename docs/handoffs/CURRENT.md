# Handoff — T-009 staged JEV decisions: review fixes merged

- **Updated:** 2026-10-17 by Claude Code
- **Branch / worktree:** task/T-009-jev-decisions @ ~/code/ms-wt/web → merged to `main` (--no-ff)
- **Status:** merged

## Next step (exact — the next agent starts here)
Claude Code: on task/T-014-policy-envelope, merge `origin/main` and start T-014 TDD-first with the
deterministic split gate on packet 02 (`docs/tasks/T-014-policy-envelope.md`).

## Done this session
All four Codex review findings (review commit `08dacd5`, cherry-picked as `e551646`), each with its
regression test:
- `b00d153` [P1] A claim citing any excluded evidence (lookahead or superseded) is dropped whole.
  Trimming ids alone leaked its text. Tested with mixed citations on packets 08 and 09.
- `5fae71f` [P2] A 200 reply whose body or `usage` isn't an object, or whose `input_tokens` is a bool,
  becomes `JevUnavailable`. `run_staged` keeps the stages that already completed.
- `bb0a2da` [P2] Score probabilities must be finite real numbers in [0, 1] (no bools or strings).
  Otherwise the judgment is omitted with `invalid_model_output`, and the other judgments survive.
- `090680a` [P2] The recorder starts a new stage only when the request body changes. A retry
  overwrites its own stage file and lists earlier statuses in `retried_statuses`. Tests now import
  `StageFiles` from the script (task-file wording updated), but never `LiveTransport`.

Recordings are unchanged: no fixture has mixed citations, and replay still hits every hash.
Codex did not re-review these fixes; Anuraag asked to merge directly.

## Tests run
- `uv run --project apps/api pytest apps/api/tests packages/contracts/tests evals/tests` → 488 passed,
  6 xfailed, 50 skipped (Postgres; no `TEST_DATABASE_URL`).
- `make lint` → exit 0.

## Contract changes proposed (not applied)
- Optional taxonomy v1.1: `interpretation_conflict` as a Noul with a policy threshold.

## Unresolved / assumptions
- Strict xfails remain: 02 split (→ T-014's deterministic gate), 03/10 evidence-only usability.
- A dropped claim is not listed in `BuiltState`. Add `excluded_claim_ids` if the audit record needs it.
- Replay can't reproduce a retry sequence, because it keeps one response per hash. That's fine
  for now.
- Carried over: billing status unverified, PyYAML runtime dependency, stage-1-unavailable envelope
  path, missing exposure for `research_relevance`, a usable-packet injection probe, T-012
  follow-ups, the T-008 non-positive close.
