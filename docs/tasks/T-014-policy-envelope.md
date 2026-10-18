# T-014 — Policy engine v1 + decision envelope

- **Implementer:** Claude Code   **Reviewer:** Codex
- **Branch:** task/T-014-policy-envelope   **Depends on:** T-009 (merged first), T-006, ADR-005   **Contract version:** v1.1 (no contract change)
- **Effort:** high reasoning (gate order, action table); default for assembly and tests

## Problem
T-009 produces staged JEV judgments, but nothing turns them into a publishable decision. Three known gaps
from the T-009 recording need deterministic code, not model tuning:
- Packet 02 (split): JEV said `partial`. An unadjusted close series across a split can't establish a move.
- Packet 07: unusable only by luck. Its missing required observations are declared as a coverage gap,
  but no code reads that gap.
- Packets 03 and 10 (evidence, no observations): JEV said `unusable`. Anuraag decided (2026-10-17) these
  are **partial, not unusable**: evidence without observations can back a hedged brief.
- `research_relevance` came back 4 for nearly everything because the state carries no portfolio exposure.

Policy precedence (`docs/evidence-policy.md#policy-precedence`) puts deterministic integrity checks first,
and `docs/project-rules.md` says policy code owns freshness gates and research actions. This task builds
that layer and the envelope assembly, so that T-010 can compare rules-only, persona and JEV on the same
envelope.

## User-visible outcome
None in the UI yet. A developer can run `decide(packet, portfolio, client)` over the 10 adversarial packets
offline, and get one schema-valid decision envelope per packet with `research_action`,
`abstention_reasons` and full version lineage. The same function runs with no model at all
(`versions.model = "rules-only"`), and when JEV is down (`"unavailable"`).

## Read (only these)
- `docs/evidence-policy.md` (policy precedence, freshness, evidence packet)
- `docs/architecture.md#decision-envelope` and the "Degraded" paragraph
- `decisions/policies/v1.yaml`, `decisions/taxonomy/v1.yaml`
- `packages/contracts/schemas/decision.schema.json`, `common.schema.json` (`research_action`, `horizon`)
- `apps/api/app/judgment/` (T-009: `StagedResult`, `build_state`, `run_staged`)
- `apps/api/app/domain/valuation.py` (`value_portfolio`, per-position `weight`)
- `evals/fixtures/packets/*/`, `evals/fixtures/portfolio/`, `evals/fixtures/README.md`

## Owned paths (edit only these)
- `apps/api/app/policy/` (new): `gates.py`, `exposure.py`, `actions.py`, `envelope.py`
- `apps/api/app/judgment/stages.py`: **only** to accept deterministic gate results and an `exposure` state
  field. No change to question wording, which would invalidate the recordings.
- `apps/api/tests/test_policy_*.py` (new)
- `decisions/policies/v1.yaml`: fill in the `TODO` weights and thresholds with values marked
  `provisional: true` (ADR-005), and add the gates below. No change to the `actions` list.
- `evals/fixtures/packets/{03,10}/expected.json`: add `"data_usability": "partial"` (Anuraag's decision).
  This is the only fixture edit. Packet hashes don't cover `expected.json`.
- `docs/tasks/T-014-policy-envelope.md`, `docs/tasks/LEDGER.md`, `docs/handoffs/CURRENT.md`
- `scripts/record_jev.py` and `evals/recordings/jev/`: added 2026-10-18 for the approved stage-3 re-recording
  (Anuraag approved ≈ $0.001). The recorder runs `decide()` and only sends requests not already recorded.

Not owned: `apps/api/app/providers/` (T-008), `packages/contracts/`, `decisions/taxonomy/v1.yaml`,
`apps/api/app/judgment/questions.py`.

## Design
Order is fixed: **gates → JEV (only if the gates allow it) → gate override → action → envelope.**

1. **`gates.py`**: pure functions over the packet. Each returns `GateResult(usability_cap, reasons,
   effects)`. The strictest cap wins: `unusable` < `partial` < `usable`.
   - `split_unadjusted`: the event is `corporate_action`, and the instrument has two or more `close`
     observations with `adjustment: none` on both sides of the event. Cap `unusable`, reason
     `unusable_input`. (Packet 02.)
   - `no_observations`: no observation remains after the exclusions, **and** `event.coverage_gaps` is
     empty. Cap `partial`, reason `no_observations`. (Packets 03, 10.) This caps the result at partial;
     it never rejects.
   - `critical_source_missing`: no observations **and** a declared coverage gap. Cap `unusable`, reasons
     `unusable_input` and `critical_source_missing`. (Packet 07, whose gap says required price
     observations are unavailable.) Gaps are free text in contract v1, so any declared gap counts as
     critical. Leave a code comment: `shortcut: any coverage gap is critical, upgrade when gaps get typed
     codes (propose v1.2)`.
   - `stale`: the latest eligible `close` for the event instrument has `observed_at` before
     `expected_session_close`. Effect `disable_time_sensitive_readiness`, cap `partial`. (Packet 05.)
     `expected_session_close` is a **parameter**, not computed here. T-008 owns exchange calendars; the
     fixtures pass `2026-09-25T20:00:00Z`. Never fall back to wall-clock time.
   - `timestamp_order_invalid`: an evidence item has `known_at` before `published_at`, or an observation
     has `received_at` before `observed_at`. Cap `unusable`.
   - The cutoff and correction exclusions stay in `build_state` (T-009). Gates see the post-exclusion
     state and report the excluded ids.
2. **`exposure.py`**: `exposure_for(event, valuation) -> Exposure | None`. Sums the valuation `weight` of
   positions in `event.instrument_ids`. If any of those positions has no market value, it returns
   `None` with reason `exposure_unavailable`, **never 0**. An instrument not held gives
   `Exposure(weight=0, held=False)`; that is a real zero, so it is kept distinct from unavailable.
   This is plain `Decimal` arithmetic and no model ever touches it.
3. **Stage-3 grounding**: `run_staged` puts `exposure` into the stage-3 state as a computed fact
   (`{"held": bool, "weight": "0.0412"}`). When exposure is `None`, stage 3 omits `research_relevance`
   and abstains with `exposure_unavailable`, mirroring `no_recorded_thesis`. This changes the stage-3
   request bodies, so stage-3 recordings must be re-recorded (≈ $0.001; Anuraag approves in chat).
   Until then, replay tests for stage 3 run against a fake transport.
4. **Override**: `final_usability = min(gate cap, JEV data_usability)`. JEV can lower usability, but never
   raise it. A gate cap of `unusable` skips JEV entirely (it saves the call), sets
   `judgments.data_usability = "unusable"` and `versions.model = "rules-only"`. When JEV says
   `unusable` but the gates cap at `partial` because only `no_observations` fired, the gate wins and the
   result is `partial`. This is the one place a deterministic rule *raises* the model's answer. It is
   allowed only for that gate, and only to `partial` (Anuraag's decision). Record the JEV answer in `raw`.
5. **`actions.py`**: a deterministic table, checked top-down, first match wins:
   | Condition | `research_action` |
   |---|---|
   | final usability `unusable`, or `evidence_sufficiency` = `insufficient` | `insufficient_evidence` |
   | stage 2 missing (classification unavailable or budget skipped) | `insufficient_evidence` + reason |
   | not held, and no thesis | `no_new_material_issue` |
   | priority index ≥ `investigate_now` and usability `usable` and not stale | `investigate_now` |
   | priority index ≥ `review_today` | `review_today` |
   | priority index ≥ `watch_condition` | `watch_condition` |
   | otherwise | `no_new_material_issue` |

   Priority index = Σ weight × normalized input over `exposure_weight` (capped at 1 at a 10% position),
   `research_relevance` ((level−1)/4), `event_materiality` (from `event_family`: a fixed map in the policy
   file) and `time_sensitivity` (0 when stale). The weights and thresholds are **provisional** in
   `policies/v1.yaml`, and T-010 replaces them. It is an index, never a probability. JEV probabilities
   are never multiplied or used here; only the validated categorical and ordinal judgments are.
   `partial` usability caps the action at `review_today`.
6. **`envelope.py`**: `decide(...) -> dict`. Builds the envelope per `decision.schema.json`:
   - `decision_id` is uuid5 over (event id, cutoff, policy version, model id), so a rerun is idempotent.
   - `as_of` = the packet cutoff. `packet_hash` comes from `event.json`.
   - `evidence_ids` are the post-exclusion ids only.
   - `versions` = {taxonomy, policy, model, calibration: null}.
   - `raw_provider_output_ref` = null for now (storage is ADR-005 follow-up).
   - `status: "published"`.
   - The envelope is validated against the schema before it is returned. A failure raises; the envelope
     is never patched.

## Invariants
- Gates are deterministic, pure, and run before any model call. JEV can't raise usability above a gate
  cap, except `no_observations` → `partial` (see 4).
- Missing exposure is `None` plus an abstention, never `0`. "Not held" is a real `0`, and the two are
  kept distinct.
- No model touches arithmetic: exposure, the priority index and the cost are all `Decimal` in code.
- Tests never open a socket. The rules-only and fake-transport paths need no recordings.
- Every envelope validates against `decision.schema.json`. `abstention_reasons` are unique and snake_case.
- The same inputs always produce byte-identical envelopes, including `decision_id`.

## Error states
- `classification_unavailable` / `budget_skipped` (from T-009): the envelope is still produced, with
  `versions.model = "unavailable"`, the gate-only `data_usability`, and `research_action =
  insufficient_evidence`. This is the "classification unavailable" degraded path from the architecture doc.
- `exposure_unavailable`: `research_relevance` is omitted and the priority index leaves out exposure and
  relevance (with the remaining weights renormalized). The action is capped at `watch_condition`.
- `stale`: `disable_time_sensitive_readiness`, so `investigate_now` is unreachable.
- Schema validation failure: raise. Never publish.

## Acceptance fixtures
- Each of the 10 packets × the fixture portfolio gives a schema-valid envelope. The checks below are
  table-driven against `expected.json`:
  - 02 → `unusable` / `insufficient_evidence` / `[unusable_input]`, with **no JEV call** (rules-only).
  - 07 → `unusable` / `insufficient_evidence`, from `critical_source_missing` and with no JEV call. The
    injected text in its evidence never reaches a model, which is the strongest guarantee. The
    injection-resistance probe itself stays a T-010 case.
  - 03, 10 → `data_usability: partial` even though the recorded JEV said `unusable`. Remove those two
    strict xfails from `test_judgment_replay.py` and replace them with policy-level assertions.
  - 05 → `partial`, effect `disable_time_sensitive_readiness`, action ≠ `investigate_now`.
  - 08, 09 → `evidence_ids` exclude `ev-2` and `ev-1` respectively.
- Unit tests:
  - Each gate fires on its trigger and not on a near-miss: an adjusted series across a split passes;
    one observation on the cutoff day is not stale; no observations without a gap is `partial`, and with
    a gap is `unusable`.
  - The exposure tests separate held, not held and unavailable.
  - Every row of the action table has its own test.
  - With a priority-index boundary exactly at a threshold, the higher action is chosen (≥), and the
    test proves it.
  - The rules-only path with `client=None` yields schema-valid envelopes for all 10 packets.
  - A stable `decision_id` across two runs.
- The T-009 xfail for packet 02 (JEV `partial`) is resolved by the gate. Remove it and assert on the
  envelope instead.

## Validation commands
```
cd apps/api && uv run pytest tests/test_policy_*.py tests/test_judgment_*.py -q
make test && make lint
```
The stage-3 re-recording (`scripts/record_jev.py --live --stage 3`) runs only after Anuraag approves it
in chat. It is about 9 calls × 2k tokens ≈ $0.001.

## Excluded scope
- An exchange calendar, and computing `expected_session_close` (T-008).
- Building packets from the database or provider data, and persisting decisions (a later api-lane task).
- Calibrated thresholds and weight fitting (T-010). The values here are provisional placeholders.
- Position-limit breach flags (no user limits model yet), the explanation writer, and the `/decisions/{id}`
  route.
- Making `interpretation_conflict` a Noul (taxonomy v1.1 proposal from T-009).

## Handoff checklist
- [x] Tests above pass (stage-3 re-recording pending approval)
- [x] `docs/handoffs/CURRENT.md` updated
- [x] LEDGER row updated
