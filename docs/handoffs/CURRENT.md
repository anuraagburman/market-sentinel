# Handoff — T-014 policy engine v1 + decision envelope: ready for Codex review

- **Updated:** 2026-10-18 by Claude Code
- **Branch / worktree:** task/T-014-policy-envelope @ ~/code/ms-wt/web (T-009 merged in via `origin/main`)
- **Status:** ready_for_review (re-recording done).

## Next step (exact — the next agent starts here)
**Codex, as a fresh session:** review against `docs/tasks/T-014-policy-envelope.md`, reading only
`git diff origin/main...origin/task/T-014-policy-envelope`. Focus on:
- `app/policy/gates.py`: the split-gate trigger (two or more distinct sessions of unadjusted closes),
  and `final_usability`'s single raise exception.
- `app/policy/actions.py`: the row order, the `>=` thresholds, and renormalization when inputs are missing.
- `app/policy/envelope.py`: how reasons are composed, and the rules-only and unavailable paths.
- `app/judgment/stages.py`: the `exposure` and `gates` parameters (the only change there).

## Done this session
- T-009: fixed all four Codex findings, and merged it `--no-ff` to `origin/main` (`bf693ca`).
  `main` is checked out in `~/code/market-sentinel`, so the merge was built here on a detached HEAD
  and pushed. That checkout's local `main` needs a `git pull`.
- T-014, test-first, one commit per step:
  - `1d78642` `split_unadjusted` gate (packet 02).
  - `d8b9a04` `sources_missing` (no_observations → partial; with a declared gap → critical/unusable),
    plus `stale` (against a caller-supplied session close), `timestamp_order_invalid`, `combine` and
    `run_gates`.
  - `cec5746` `exposure_for`: held, not held (a real 0), and unavailable (None). Works at 34-digit
    precision.
  - `ff0da93` Stage 3 gets `exposure` as a fact. When exposure is missing, `research_relevance` is
    omitted and stage 3 abstains with `exposure_unavailable`.
  - `9b785c1` The action table and policy **v1.1**. Weights, thresholds and event materiality are
    `provisional: true` Decimal strings, and the integrity gates are documented.
  - `b6cdf7e` `run_staged(gates=...)` applies `final_usability` right after stage 1.
  - `4a95084` `decide()` envelope: idempotent uuid5 `decision_id`, validated against the schema
    before it is returned.
  - `e019879` The 02/03/10 xfails are retired into envelope assertions. 03 and 10 `expected.json`
    gain `data_usability: partial`.

## Decisions made while implementing (check in review)
- **03/10 reach stage 2.** Without the gate inside `run_staged`, JEV's `unusable` stops the run, and the
  override could never classify anything. With it, stage 2 runs for 03/10. Those requests were never
  recorded, so offline they replay as unavailable and the action is `insufficient_evidence`.
- **Split gate:** it counts distinct sessions, so two feeds reporting one session's close don't fire it.
- **Reason sets:** 07 gets `[unusable_input, critical_source_missing]`, and 03/10 get `no_observations`.
  Their `expected.json` lists fewer reasons, so the acceptance test asserts expected ⊆ actual.
  07's `expected.json` isn't owned, so it wasn't edited.
- **Rules-only** always ends in `insufficient_evidence` with `classification_unavailable` (action row 2).
  `versions.model` tells it apart from a provider outage.
- `horizon` is a `decide()` parameter, defaulting to `swing`. The spec doesn't name one.
- Unavailable exposure caps the action at `watch_condition`. `partial` usability can't reach
  `investigate_now`, because that row requires `usable`.

## Tests run (branch tip)
- `make test` → pytest 582 passed, 2 xfailed (T-008 producer gap), 50 skipped (Postgres; no
  `TEST_DATABASE_URL`). Vitest: 64 passed.
- `make lint` → exit 0.

## Re-recording (done 2026-10-18)
- Anuraag ran the approved `record_jev.py --live`: 10 new calls, 19,168 input tokens, **$0.000805**,
  all 200 with no retries. There are now 28 recordings. Envelope replay is strict, so an unrecorded
  request fails the test, and it snapshots all 10 packets (`test_policy_envelope.py`).
- `423164e`: the first attempt failed with a 401 (bad key), and the recorder overwrote packet 01's good
  stage-3 file. The file was restored from Git, and the recorder now writes only 200s (with a test).
- **For T-010:** grounding barely moved `research_relevance`. It is 4 for a 48.8% position (01) and also
  4 for a 1.1% position (05), and 3 for 06 (3.8%) and 10 (3.1%). Relevance does not track exposure, so
  the priority index should not lean on it until it's calibrated.
- Outcomes: 04, 06, 08 `review_today`; 03, 05 `watch_condition`; the rest `insufficient_evidence`.
  No packet reaches `investigate_now`: every JEV usability is `partial`, and that row needs `usable`.

## Contract changes proposed (not applied)
- v1.2: typed coverage-gap codes (see the `shortcut:` comment in `gates.py`).
- Optional taxonomy v1.1: `interpretation_conflict` as a Noul.

## Unresolved / assumptions
- Promote `pyyaml` and `jsonschema`/`referencing` to runtime dependencies when the API runs `decide()`;
  `pyproject.toml` isn't owned. Both are imported lazily.
- `raw_provider_output_ref` is null (raw storage is an ADR-005 follow-up). JEV's own stage-1 answer is
  in `StagedResult.raw`, but `decide()` returns only the envelope.
- A dropped claim isn't listed in `BuiltState` (from the T-009 fixes).
- Carried over: billing status unverified, a usable-packet injection probe (T-010), T-012 follow-ups,
  T-008's non-positive close, an exchange calendar for `expected_session_close` (T-008).
