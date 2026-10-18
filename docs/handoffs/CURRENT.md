# Handoff — T-014 policy engine v1 + decision envelope: approved

- **Updated:** 2026-10-18 by Codex
- **Branch / worktree:** review/T-014-policy-envelope @ ~/code/ms-wt/api
- **Status:** ready_to_merge

## Next step (exact — the next agent starts here)
Integrate this review documentation into task/T-014-policy-envelope, then merge T-014 to main
with `--no-ff` and push main. Codex approves implementation tip `c3b22b4` for that merge.
No merge was performed in this review session; main belongs to the integration worktree.

## Done this session
- Re-reviewed `git diff 7bcbdab..c3b22b4`, including both regression tests and surrounding gate,
  envelope, action-table and staged-failure handling. No remaining findings in this fix scope.
- `0fff4cc`: an outage at any stage discards partial model judgments from the envelope, retains
  gate-only usability and reports model unavailable with insufficient_evidence.
- `6c78572`: split detection counts distinct sessions per event instrument, so separate instruments
  with one close each cannot combine into a false split gate.
- Used an isolated review branch because the implementation branch is checked out in the web
  worktree. No live provider calls, recordings or implementation changes.

## Tests run
- `make test` → 597 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed.
- `make lint` → passed (Ruff, formatting, ESLint, Next type generation, TypeScript).
- `git diff 7bcbdab..HEAD --check` → passed.
- Initial sandbox runs could not access the uv cache; approved reruns completed successfully.

## Contract changes proposed (not applied)
- None in this review. Carry forward typed coverage-gap codes (v1.2) and optional
  interpretation_conflict Noul proposal.

## Unresolved / assumptions
- Approval covers the two requested fixes against the existing T-014 review baseline.
- 50 database tests require Postgres/TEST_DATABASE_URL; two existing T-008 xfails remain.
- Carry forward runtime dependency promotion (pyyaml, jsonschema/referencing), raw-output storage,
  excluded-claim audit ids, billing-status verification, usable-packet injection probe, T-010
  relevance calibration, T-012 follow-ups, T-008 non-positive close and exchange calendar.
