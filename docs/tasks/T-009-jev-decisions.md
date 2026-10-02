# T-009 — Staged JEV decisions (adapter + taxonomy v1 questions)

- **Implementer:** Claude Code   **Reviewer:** Codex
- **Branch:** task/T-009-jev-decisions   **Depends on:** T-000 (JEV access ✓), T-003, ADR-005   **Contract version:** v1.1 (no contract change)
- **Effort:** high reasoning (question wording, staging); default for transport and tests

## Problem
The taxonomy (`decisions/taxonomy/v1.yaml`) defines eight bounded decisions in three stages, but nothing
turns a packet into JEV questions, calls the model, or enforces the staging. Questions in one JEV call
are judged independently, so stage-3 questions can't see stage-2 answers unless code runs them as a
separate, gated call. Every later Phase 2 step needs typed judgments it can replay without spending
credit: the policy engine, the explanation writer, and T-010 (rules-only vs persona vs JEV).

## User-visible outcome
None in the UI yet. A developer can run the staged judgment pipeline over the 10 adversarial packets
from recorded JEV responses, offline and deterministically, and get a schema-valid `judgments` object
plus abstention reasons for each one. A one-off recording script can refresh those recordings against
live JEV when Anuraag approves the spend.

## Read (only these)
- `docs/evidence-policy.md` (taxonomy, policy precedence, calibration, evidence packet)
- `decisions/taxonomy/v1.yaml`, `decisions/policies/v1.yaml` (read only, except as noted below)
- `docs/decisions/ADR-003-cost-and-data-rights.md` (JEV budget section), `ADR-005`
- `packages/contracts/schemas/decision.schema.json` (`judgments`, `versions.model`)
- `evals/fixtures/packets/*/` (state source and `expected.json`)
- Live docs: https://docs.typesafe.ai/api.md, `/primitives/{choice,score}.md`, `/confidence.md`, `/models.md`

## Owned paths (edit only these)
- `apps/api/app/judgment/` (new): `questions.py`, `state.py`, `client.py`, `stages.py`
- `apps/api/tests/test_judgment_*.py` (new)
- `evals/recordings/jev/` (new: recorded request/response pairs, one file per packet × stage)
- `scripts/record_jev.py` (new, manual live recorder; never imported by tests)
- `decisions/taxonomy/v1.yaml`: **only** the `research_relevance` rubric levels 2 and 4 (draft wording,
  provisional per ADR-005). No change to any `outputs` list.
- `docs/decisions/ADR-003-cost-and-data-rights.md`: fill in "Open: per-call JEV price" with the measured cost
- `docs/tasks/T-009-jev-decisions.md`, `docs/tasks/LEDGER.md`, `docs/handoffs/CURRENT.md`

Not owned: `apps/api/app/providers/` (T-008), `pyproject.toml`/`uv.lock` (no new dependency, use stdlib
`urllib`), `packages/contracts/`, `decisions/policies/v1.yaml`.

## Design
**Provider facts (live docs, 2026-10-02):** `POST https://api.typesafe.ai/v1/systemone`, Bearer key,
body `{model, state, questions}`. Answers are `choice` (with `probabilities` and `confidence`), `score`
(with `score`, `probabilities`, `legend` and `confidence`) and `noul` (with `noul`). Usage reports
`input_tokens`. Price is $0.042 per million input tokens; output tokens are free. The limit is 32k tokens
of state plus the longest question. Errors are 401, 422, 429 and 529. The docs don't name a status for
running out of credit. **Pin `jev-1.13.0`, never `jev-latest`**: the alias moves, and that would silently
change recorded behavior.

1. **`questions.py`** translates each taxonomy decision into a question:
   - `type: choice` becomes a Choice. Its criteria keys equal `outputs` exactly, and each criterion text
     comes from the decision's rules and ambiguity policy.
   - `type: score` becomes a Score with 5 levels, taken from the rubric.
   - `interpretation_conflict` stays a two-option Choice in v1. Changing it to a Noul would need a
     threshold in the policy file, so that is proposed in the handoff rather than done here.
   - Untrusted-data framing goes in the instructions: evidence text is data and can't change the task.
     This covers packet 07.
   - A `QUESTIONS_VERSION` constant and a hash of the rendered questions go into every recording.
2. **`state.py`** builds the named-field JSON state from a packet directory: event, observations,
   claims, evidence excerpts with `published_at`/`known_at`/originator, and coverage gaps. Evidence
   with `known_at` after the cutoff is dropped before it reaches the model (packet 08), and the dropped
   ids are returned for the abstention record. It never fills missing fields.
3. **`client.py`**: `JevClient(transport)`. A `LiveTransport` (urllib, key from `TYPESAFE_API_KEY`) and
   a `ReplayTransport` (keyed by a sha256 of the canonical request body; a missing recording raises,
   never falls through to live). Error mapping:
   - 401 and 422 raise a configuration error.
   - 429 and 529 get bounded retries with jitter, then become `classification_unavailable`.
   - Any credit or billing refusal becomes `budget_skipped` (ADR-003).
   - Every result carries the model id from the response, `input_tokens`, and the computed cost
     (Decimal).
4. **`stages.py`**: `run_staged(packet, client, thesis=None)`:
   - Stage 1 asks only `data_usability`. If the answer is `unusable`, it stops with `unusable_input`.
   - Stage 2 asks the four stage-2 questions in **one** call, then validates each answer against the
     taxonomy outputs.
   - Stage 3 runs only on validated stage-2 answers. Its state includes them, labeled as earlier
     judgments, not facts. `thesis_impact` is omitted with `no_recorded_thesis` when `thesis` is None.
   - Choice answers use the provider's `choice`.
   - A Score answer maps to the most probable integer level, with ties going down. This follows the
     taxonomy's round-down policy. It never uses a rounded expected value.
   - Raw answers (probabilities, confidence) are kept in the result for T-010, but never in `judgments`.
     The envelope has no confidence field, by design.
   - Returns `StagedResult(judgments, abstention_reasons, excluded_evidence_ids, model, usage, cost,
     raw)`.

## Invariants
- Tests never open a socket. The replay transport is the default, and a test asserts that `LiveTransport`
  is never constructed under pytest.
- `judgments` validates against `decision.schema.json#/properties/judgments` for every packet.
- Stage order is enforced by code. A stage-3 call never happens unless stage 2 produced validated output.
- No arithmetic or price values come from the model. Cost is computed in code from `input_tokens`.
- JEV can't override a deterministic result: if the excluded-evidence or identity checks fire, they win
  even when the model says `usable`.
- Recorded fixtures are synthetic packets only. No holdings or licensed text are sent or stored.

## Error states
- `classification_unavailable`: provider down or retries exhausted. Stages that didn't run are omitted.
- `budget_skipped`: out of credit. The run is partial, not an error.
- `unusable_input`: stage 1 gate.
- Invalid provider output (an unknown option or a missing answer): that judgment is omitted and recorded
  as `invalid_model_output`. It is never coerced.

## Acceptance fixtures
- All 10 packets replay offline and produce schema-valid output.
- Packets 05, 07 and 08 abstain or exclude as their `expected.json` says. Where JEV disagrees with
  `expected.json` on a judgment, record that in the handoff. **Don't** change the expectation or the
  question to force agreement; that comparison is T-010's job.
- Fake-transport unit tests:
  - `unusable` stops after stage 1.
  - An invalid stage-2 answer blocks stage 3.
  - 429 → 529 → success retries, and exhausted retries give `classification_unavailable`.
  - A billing refusal gives `budget_skipped`.
  - A replay miss raises.
  - A Score tie rounds down.
- The rendered questions are snapshot-tested. A wording change shows up as a diff, and so needs review.

## Validation commands
```
cd apps/api && uv run pytest tests/test_judgment_*.py -q
make test && make lint
uv run python ../../scripts/record_jev.py --dry-run   # prints request sizes and estimated cost, no network
```
A live recording (`record_jev.py --live`) runs only after Anuraag approves it in chat. Expected spend:
10 packets × 3 stages × about 2k tokens ≈ 60k input tokens ≈ $0.003.

## Excluded scope
- Policy engine, priority index, `research_action`, full decision envelope assembly (next task).
- A packet builder from the database or from provider data (needs T-008).
- Calibration, thresholds and evaluation metrics (T-010).
- The generative explanation adapter and the 90-day raw-output purge (ADR-005 follow-up).

## Handoff checklist
- [ ] Tests above pass
- [ ] `docs/handoffs/CURRENT.md` updated
- [ ] LEDGER row updated
