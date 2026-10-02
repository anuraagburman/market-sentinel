# Handoff — T-009 staged JEV decisions: ready for Codex review

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** task/T-009-jev-decisions @ ~/code/ms-wt/web
- **Status:** ready_for_review. Codex reviews when T-008 allows; there's no rush, because nothing depends
  on this until T-010.

## Next step (exact — the next agent starts here)
**Codex, as a fresh session on this branch:** review against `docs/tasks/T-009-jev-decisions.md`.
Read only `git diff origin/main...task/T-009-jev-decisions`. Focus on:
- `app/judgment/client.py`: the error mapping, and the guard that stops replay from ever going live.
- `app/judgment/stages.py`: the gating, and how Score answers map to levels.
- `app/judgment/state.py`: the cutoff and correction exclusions.
- The strict xfails in `tests/test_judgment_replay.py`.

Report findings with file:line and a test that would catch each one.

## Done this session
- `8f87748` Spec.
- `eace03c` Taxonomy → JEV questions, with provisional rubric levels 2 and 4.
- `aab9414` Packet state with deterministic exclusions.
- `6f2b767` Client pinned to `jev-1.13.0`, with record/replay and error mapping.
- `b53c327` Gated three-stage runner.
- `8e42914` Recorder script.
- `7dda088` Anuraag's live recording: 10 packets, 24 calls. The replay test snapshots every judgment.
- `b768da2` ADR-003 measured cost: **$0.00007 per call**, $0.00167 for the batch.
- `8577ade` Recordings moved to `evals/recordings/jev/`.
  `evals/tests/test_fixtures.py` schema-checks every JSON under `evals/fixtures/`, and recordings aren't
  contract entities. ADR-005's "under `evals/fixtures/`" wording means the same intent: they are test
  data and not purged. T-008's `evals/fixtures/providers/` will hit the same test.

## JEV vs expected.json (tracked as strict xfails; not tuned)
| Packet | Expected | JEV (stage-1 probability) | Reading |
|---|---|---|---|
| 02 split | `unusable` | `partial` (0.67; unusable 0.25) | The taxonomy says a split move is a normalization suspect. That belongs in a deterministic integrity gate, not the model. Add it to the policy/envelope task. |
| 03 syndicated | no abstention | `unusable` (0.74) | The packet has no observations. Is an evidence-only packet unusable? That is a fixture/taxonomy question for Anuraag. |
| 10 failed coverage | no abstention (partial brief) | `unusable` (0.59) | Same cause (no observations). Low confidence. |

Agreements: 05 `partial`, 07 `unusable`, 08 and 09 exclusions, and `event_family` matches `event_type`
on all 7 packets that reached stage 2.

Caveats:
- **07 is not evidence of injection resistance.** The fixture README says 07 also lacks its required
  observations, so "unusable" is justified without the injection. An injection probe on an otherwise
  usable packet would test resistance properly (a T-010 robustness case).
- **`research_relevance` is ungrounded.** It came back 4 for 8 of the 9 packets that reached stage 3, but
  the state carries no portfolio exposure, which the taxonomy requires. Relevance should abstain, or be
  given exposure, once the envelope task builds packets from portfolios.
- `primary_context` is `unknown` on 8 of 9: no packet carries benchmark or sector moves. That fits the
  ambiguity policy.

## Tests run (branch tip `8577ade`)
- `pytest apps/api/tests packages/contracts/tests evals/tests` → 462 passed, 6 xfailed (2 from the T-008
  producer gap, 4 tracked JEV disagreements), 50 skipped (Postgres: no `TEST_DATABASE_URL` in this shell;
  T-009 doesn't touch the DB).
- Vitest → 64 passed.
- `make lint` → exit 0.

## Contract changes proposed (not applied)
- Optional taxonomy v1.1: make `interpretation_conflict` a Noul (TypeSafe's yes/no primitive), with its
  threshold in `decisions/policies/`.

## Unresolved / assumptions
- The docs give no HTTP status for running out of credit. The client treats 402, or a non-retryable error
  mentioning credit, billing, balance, payment or quota, as `budget_skipped`. Confirm this when credit
  first runs out.
- `questions.py` imports `pyyaml`, which is only a dev dependency. Promote it when the API runs the
  pipeline.
- If stage 1 fails, `judgments` is empty. The envelope requires `data_usability`, so it needs a
  "classification unavailable" path.
- Next task in this lane (no spec yet): policy engine plus decision envelope. It covers the deterministic
  split and freshness gates, exposure in the state, `research_action`, and the unavailable path.
- Carried forward:
  - T-012 follow-ups: UNIQUE on `import_confirmations.portfolio_version_id`, the composite tenant FK,
    the `seed_fixture` head guard, pruning preview locks, an explicit preview upsert, and the
    `.env.example` `MS_ENV` default.
  - T-008: the non-positive close gap.
  - Upload size limit, per-tenant keys, observation persistence, and the /briefs projection formatter.
