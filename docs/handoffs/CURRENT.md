# Handoff — T-009 staged JEV decisions (code done; live recording pending)

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** task/T-009-jev-decisions @ ~/code/ms-wt/web
- **Status:** in_progress. It's blocked on one live recording run that Anuraag must approve and run.
  Codex is working on T-008 in parallel (~/code/ms-wt/api).

## Next step (exact — the next agent starts here)
1. **Anuraag, in a terminal** (the key stays out of the agent's view):
   ```
   cd ~/code/ms-wt/web
   set -a; source ~/.config/market-sentinel/.env; set +a   # must define TYPESAFE_API_KEY
   uv run --project apps/api python scripts/record_jev.py --live
   ```
   The dry run estimates about 35k input tokens, roughly $0.0015 in total. This writes
   `evals/fixtures/jev/<packet>/stage-<n>.json`.
2. **Claude Code:**
   - Add `apps/api/tests/test_judgment_replay.py`: all 10 packets replay offline, each `judgments`
     validates against the schema, and 02, 07 and 08 match their `expected.json` gates.
   - Commit the recordings. Record the measured cost per call in ADR-003 "Open".
   - List every disagreement between JEV and `expected.json` here. Don't tune questions to remove them.
   - Mark the task `review` for Codex.

## Done this session
- Spec `docs/tasks/T-009-jev-decisions.md` (`8f87748`).
- `app/judgment/questions.py` renders taxonomy v1 as Choice and Score questions. The provisional
  `research_relevance` rubric levels 2 and 4 are drafted in `decisions/taxonomy/v1.yaml` (`eace03c`).
- `state.py` builds the packet state. Evidence or observations first known after the cutoff are excluded,
  and so are originals superseded by a correction (`aab9414`).
- `client.py` is pinned to `jev-1.13.0`, uses stdlib HTTP, and has record/replay transports and error
  mapping (`6f2b767`).
- `stages.py` runs the three gated stages (`b53c327`).
- `scripts/record_jev.py` supports `--dry-run` and `--live` (`8e42914`).

## Tests run
- `make test` → 442 pytest passed, 2 xfailed (T-008 producer gap), and 50 skipped (Postgres: no
  `TEST_DATABASE_URL` in this shell; T-009 doesn't touch the DB). 64 Vitest passed.
- `make lint` → exit 0.
- `record_jev.py --dry-run` → sizes printed, no network.

## Contract changes proposed (not applied)
- Optional taxonomy v1.1: make `interpretation_conflict` a Noul (TypeSafe's yes/no primitive), with its
  threshold in `decisions/policies/`. For v1 it stays a two-option Choice.

## Unresolved / assumptions
- The docs give no HTTP status for running out of credit. The client treats 402, or any non-retryable
  error whose message mentions credit, billing, balance, payment or quota, as `budget_skipped`. Confirm
  this the first time credit actually runs out.
- `questions.py` imports `pyyaml`, which is only a dev dependency. Promote it to a runtime dependency
  when the API calls the pipeline.
- `data_usability` sees raw observations. No deterministic `freshness_state` field exists yet; that
  belongs to the policy engine and envelope task (next in this lane).
- If stage 1 fails, `judgments` is empty. The envelope requires `data_usability`, so envelope assembly
  needs a "classification unavailable" status path.
- Carried forward:
  - T-012 follow-ups: UNIQUE on `import_confirmations.portfolio_version_id`, the composite tenant FK,
    the `seed_fixture` head guard, pruning preview locks, an explicit preview upsert, and the
    `.env.example` `MS_ENV` default.
  - T-008: the non-positive close gap.
  - Upload size limit, per-tenant keys, observation persistence, and the /briefs projection formatter.
