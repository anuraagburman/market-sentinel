# Handoff — T-010 first eval report: ready (spec written)

- **Updated:** 2026-10-18 by Claude Code
- **Branch / worktree:** main (spec only); implementation goes on `task/T-010-first-eval-report` in `~/code/ms-wt/api`
- **Status:** ready

## Next step (exact — the next agent starts here)
Codex, fresh session in `~/code/ms-wt/api`: create `task/T-010-first-eval-report` from `main` and follow
`docs/tasks/T-010-first-eval-report.md`. Write `evals/tests/test_eval_harness.py` first with a fake persona
transport. Run `scripts/record_persona.py --dry-run` and **stop for Anuraag's approval** before `--live`.

## Done this session
- T-015 merged to main (`8a1dfb5`, `--no-ff`) after Codex's approval (`7c37d32`), plus one review fix
  (`56c79e4`): `test_labels.py` now rejects values of the wrong type (`true` for 1, `4.0` for 4).
- T-010 spec written. Persona model corrected to `claude-haiku-4-5` ($1/$5 per million tokens). The
  earlier `claude-haiku-5-5` doesn't exist. Persona runs through `decide()`, so all three arms share
  the gates and staging. Denominators come from the label files, not the README table (review finding 2).

## Tests run
- `make test` on merged main → 608 Python passed, 50 skipped, 2 xfailed; 64 Vitest passed. `make lint` passed.
- The main checkout first failed Vitest/lint because its `node_modules` was missing `ajv`. `npm ci` fixed it;
  the code was unaffected. Note: main was pushed before this re-run (a pipeline only checked `tail`'s exit code).

## Contract changes proposed (not applied)
- None. Carry forward typed coverage-gap codes (v1.2) and the optional interpretation_conflict Noul proposal.
- T-015's proposed `TODO(label)` example text for `decisions/taxonomy/v1.yaml` is listed in commit `cf1eb26`'s handoff.

## Unresolved / assumptions
- The persona estimate (about 28 calls, about $0.10) is based on recorded JEV request sizes; the dry run gives the real number.
- The persona transport has to map Claude's structured output into JEV's response shape. If that needs a
  hook in `apps/api/app/`, Codex proposes it in the handoff (not owned by T-010).
- Carry forward from T-014: runtime dependency promotion (pyyaml, jsonschema/referencing), raw-output storage,
  excluded-claim audit ids, billing-status verification, usable-packet injection probe, T-012 follow-ups,
  T-008 non-positive close and exchange calendar.
