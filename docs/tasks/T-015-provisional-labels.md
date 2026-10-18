# T-015 — Provisional labels + labeling rubric for the 10 fixture packets

- **Implementer:** Claude Code (drafts) + Anuraag (approves every label)   **Reviewer:** Codex
- **Branch:** task/T-015-provisional-labels   **Depends on:** T-003, T-009   **Contract version:** v1.1
- **Effort:** high reasoning (labels are the ground truth T-010 scores against)

## Problem
T-010 compares rules-only, persona and JEV on the same packets, but there is little to score against.
`expected.json` labels only a few fields: `data_usability` on 5 packets, `research_action` on 2,
exclusions on 2 and freshness on 1. Six of the eight taxonomy v1 decisions have no labels at all.
Without labels for every decision, T-010 can only measure policy-gate behavior.

## User-visible outcome
Each of the 10 packets has one label file that gives an answer, or a reasoned abstention, for every
taxonomy v1 decision. Every label carries a one-line rationale and `status: provisional`. A short rubric
says how each decision was labeled, so a later practitioner can audit the labels or relabel.

## Read (only these)
- `docs/evidence-policy.md#calibration-and-evaluation`
- `docs/decisions/ADR-005-retention-and-label-review.md` (labels are provisional, Anuraag approves)
- `decisions/taxonomy/v1.yaml` (outputs, rules, ambiguity_policy, abstain_when, research_relevance rubric)
- `evals/fixtures/README.md` and each `evals/fixtures/packets/*/` (event, evidence, claims, observations, expected)
- `evals/tests/test_fixtures.py` (packet hash function and the expected.json schema, to stay consistent)

**Blind labeling: don't read** `evals/recordings/`, recorded JEV answers, or policy-engine output for
these packets before every label is approved. Labels written after seeing model answers are not
independent baselines.

## Owned paths (edit only these)
- `evals/labels/v1/<packet-id>.json` (new, one per packet)
- `evals/labels/README.md` (new: the rubric and the labeling procedure)
- `evals/tests/test_labels.py` (new)
- `docs/tasks/T-015-provisional-labels.md`, `docs/tasks/LEDGER.md`, `docs/handoffs/CURRENT.md`

Not owned: `decisions/taxonomy/v1.yaml`, where filling in `TODO(label)` examples is a taxonomy change.
Propose example text in the handoff instead. Also not owned: `expected.json` and `generate.py`.

## Inputs / outputs
Each label file holds:
```json
{
  "packet": "03-syndicated-single-source",
  "packet_hash": "sha256:…",          // same hash function as test_fixtures.py; ties labels to the frozen packet
  "taxonomy_version": "1.0",
  "status": "provisional",
  "labeler": "anuraag",              // Claude Code drafts; Anuraag is the labeler of record after approval
  "labeled_at": "2026-10-…",
  "labels": {
    "data_usability":   {"value": "partial", "why": "…"},
    "novelty":          {"value": "repeated", "why": "…"},
    "thesis_impact":    {"abstain": "no_recorded_thesis", "why": "…"},
    "research_relevance": {"value": 2, "why": "…"},
    "…": {}
  },
  "research_action": {"value": "…", "why": "…"}   // optional; only where the packet determines it
}
```
Each decision gets either `value` or `abstain`, never both and never neither. `why` is a single line.
It names the packet field or evidence id it relies on.

## Invariants
- Every taxonomy v1 decision id appears in every file. No extra ids.
- A `value` is in that decision's `outputs`. An `abstain` is in that decision's `abstain_when`, or is
  `unusable_input` when `data_usability` is `unusable`. In that case, stages 2–3 abstain because they
  never run.
- Labels agree with `expected.json` wherever both state a field. A disagreement is a finding to raise
  with Anuraag, never a reason to edit either file to make them match.
- Labels judge as-of the packet cutoff only. Evidence that `expected.json` excludes (08's ev-2,
  09's ev-1) is not used.
- Labels follow each decision's `ambiguity_policy`, such as `unknown` rather than a guessed driver, and
  rounding down `research_relevance`.
- `packet_hash` matches the current fixture. If a fixture is regenerated, the test fails and the
  labels must be re-checked.

## Error states
- A packet that can't support a confident label for a decision gets the ambiguity-policy answer, such as
  `unknown`, `unclear` or `partial`, and a `why` that says what is missing. Never invent a value.
- If Anuraag rejects a drafted label, use Anuraag's value and keep their reason as the `why`.

## Acceptance fixtures
- All 10 packets: `evals/labels/v1/01-…json` through `10-…json`.
- Per-decision label counts and abstention counts are listed in the README, so T-010 knows its
  denominators (expect n≤10 per decision, and fewer for stage-3 decisions).

## Validation commands
```
cd apps/api && uv run pytest ../../evals/tests/test_labels.py -q
make test && make lint
```
`test_labels.py` checks the invariants above against `decisions/taxonomy/v1.yaml`, `expected.json`,
and the packet hash. It makes no network calls.

## Excluded scope
- Second-labeler agreement and adjudication. ADR-005 has no practitioner engaged yet.
- New packets, or growing toward the 60–100 dev cases.
- Any change to the taxonomy, question wording, or recordings.
- Scoring models against labels (T-010).

## Handoff checklist
- [x] Every label approved by Anuraag in chat (record the approval date in the handoff)
- [x] Tests above pass
- [x] Proposed `TODO(label)` example text listed in the handoff (not applied)
- [x] `docs/handoffs/CURRENT.md` updated
- [x] LEDGER row updated; T-010 spec can then be written
