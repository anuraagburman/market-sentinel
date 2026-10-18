# Handoff — T-010 first eval report: live run approved; credential missing

- **Updated:** 2026-10-18 by Codex
- **Branch / worktree:** task/T-010-first-eval-report @ ~/code/ms-wt/api
- **Status:** in_progress

## Next step (exact — the next agent starts here)
Anuraag approved the persona live run in chat on 2026-10-18 ("Yes please"). The attempted run
stopped locally before any API request because no Anthropic authentication was available.
Make ANTHROPIC_API_KEY available securely to the execution environment, then run
`uv run --project apps/api python scripts/record_persona.py --live`. Approval persists; do not
ask again. Record the actual usage cost here. Generate the report with
`PYTHONPATH=apps/api:. uv run --project apps/api --locked python -m evals.harness.evaluate`, then
run `make eval-smoke`, `make test`, `make lint`, inspect findings and commit recordings/report.

## Done this session
- Anuraag approved --live in chat on 2026-10-18. Attempted the approved run; SDK authentication
  validation failed before sending a request. No recordings created, no usage cost ($0).
- Created the task branch from main. Added offline evaluation/scoring/report generation and the
  plain persona transport, recorder, structured-output enum schema and Anthropic SDK dependency.
- Persona uses decide() and the existing staged interface without application-code changes.
  Live client construction is restricted to --live; fake transports cover offline tests.
- Recorder preserves raw persona responses, replays existing stage files, and rejects changed
  request hashes or persona prompts/schemas. Report replay fails with packet/stage on missing records.
- Added 11 deterministic harness tests: scoring/confusion/±1, label-derived denominators,
  abstentions, fake persona staging, policy bypass detection, malformed-response outage,
  deterministic report, recording/replay and prompt-change rejection.
- make eval-smoke now checks the generated report; it intentionally fails until persona recordings
  and the final report exist. No persona calls made; no generated report committed yet.
- Dry run: 24 reachable calls, 129992 request bytes, ~32498 input tokens; estimated $0.155378
  including max 1024 output tokens per call. Bytes/4 is approximate; answers affect stage count.
  02 and 07 skip the model. Estimate differs from the spec's earlier ~28 calls / ~$0.10.

## Tests run
- `uv run --project apps/api python scripts/record_persona.py --live` → failed locally: missing
  authentication; no API requests sent.
- `uv run --project apps/api python scripts/record_persona.py --dry-run` → passed, no live calls.
- `make test` → 618 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed.
- `make lint` → passed.
- After replay-integrity fix, targeted suite → 11 passed; Ruff check/format on new Python files passed.
- `make eval-smoke` → expected failure: missing persona/01-earnings-no-expectations stage-1 recording.

## Contract changes proposed (not applied)
- None. Existing interface supports the persona adapter; no app/ hook needed.
- Carry forward typed coverage-gap codes (v1.2) and optional interpretation_conflict Noul proposal.

## Unresolved / assumptions
- Live run approved 2026-10-18 but could not execute without authentication. Attempt cost $0;
  completed-run cost and three-arm report findings pending. Do not put credentials in Git or chat.
- SDK pinned to anthropic 1.15.0, verified locally to accept output_config. Actual provider acceptance
  of the structured schema remains a live-run check. Provider exceptions stop execution; completed
  stage files are retained. Null decision answers abstain through existing invalid-output handling;
  malformed/refused provider content degrades to gate-only through classification_unavailable.
- Carry forward runtime dependency promotion (pyyaml, jsonschema/referencing), raw-output storage,
  excluded-claim audit ids, billing-status verification, usable-packet injection probe, T-012
  follow-ups, T-008 non-positive close and exchange calendar.
