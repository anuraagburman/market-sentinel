# T-010 — First evaluation report: rules-only vs persona vs JEV

- **Implementer:** Codex   **Reviewer:** Claude Code (Anuraag approves the live persona run)
- **Branch:** task/T-010-first-eval-report   **Depends on:** T-009, T-014, T-015   **Contract version:** v1.1
- **Effort:** high reasoning for scoring and the report; default for wiring

## Problem
Phase 2 exits on "first labeled set vs rules-only and persona baselines" (`docs/delivery.md`). T-015
labeled all eight taxonomy decisions on the 10 fixture packets, and T-009/T-014 recorded JEV on them.
Nothing yet runs the three arms over the same packets or scores them against the labels. Without that,
there's no evidence that engineered JEV adds anything over the policy gates or a plain prompt.

## User-visible outcome
`evals/reports/T-010-preliminary.md` is a committed report, generated offline from recordings. For
each arm and decision it shows agreement with the labels, a confusion table, abstention coverage and
a policy-bypass check. It shows n everywhere, and every metric is marked **provisional** (ADR-005).
`make eval-smoke` regenerates the report and fails if it changes.

## Read (only these)
- `docs/evidence-policy.md#calibration-and-evaluation`, `docs/delivery.md` (release gates, phase 2)
- `evals/labels/README.md` and `evals/labels/v1/*.json` (ground truth, procedure, known limits)
- `apps/api/app/policy/envelope.py` (`decide`), `apps/api/app/judgment/client.py` (transports),
  `apps/api/app/judgment/stages.py`, `scripts/record_jev.py` (recording pattern to copy)
- `apps/api/tests/test_policy_envelope.py` (how recordings are replayed in tests)

## Owned paths (edit only these)
- `evals/harness/` (new: scoring and report generation)
- `evals/recordings/persona/<packet>/stage-<n>.json` (new, written once by the live run)
- `scripts/record_persona.py` (new)
- `evals/reports/T-010-preliminary.md` (generated, committed)
- `evals/tests/test_eval_harness.py` (new)
- `Makefile` (`eval-smoke` target only), `apps/api/pyproject.toml` + `apps/api/uv.lock` (add `anthropic`)
- `docs/tasks/T-010-first-eval-report.md`, `docs/tasks/LEDGER.md`, `docs/handoffs/CURRENT.md`

Not owned: `evals/labels/`, `evals/fixtures/`, `evals/recordings/jev/`, `decisions/`, `apps/api/app/`.
If an arm needs a change in `app/`, propose it in the handoff.

## The three arms (same 10 packets, same fixture portfolio, same `expected_session_close`)
| Arm | How it runs |
|---|---|
| rules-only | `decide(packet, valuation, client=None)`. Only the gate outputs (`data_usability` cap, research_action). Every other decision counts as an abstention (`not_run`). |
| persona | `decide()` with a client whose transport sends the **same staged questions** (`render_stage`) and packet state to `claude-haiku-4-5` under one plain system prompt ("You are an experienced US-equity trader…"). It gets no taxonomy rules beyond what the questions already carry, and no JEV-specific engineering. Answers are mapped into the response shape `decide()` expects, so the gates, staging and actions are identical to JEV's. |
| JEV | `decide()` with `ReplayTransport(evals/recordings/jev/<packet>)`. No new JEV calls. |

The persona transport uses structured outputs (`output_config.format`), with one enum per decision
plus an abstain option. It records with the same pattern as `record_jev.py`: `--dry-run` prints sizes
and an estimated cost; `--live` spends credit, reads the Anthropic credential from the environment,
records each request/response once, and replays from then on.

## Metrics (per arm × decision; n from the label files, never from the README table)
- **Agreement** on packets where the label has a `value`, with an exact-match count. For
  `research_relevance`, also report within ±1.
- **Confusion table** of label value against arm value, including abstention as its own column.
- **Abstention coverage:** of the label's abstentions, how many the arm also abstained on. Of the
  label's answered cases, how many the arm abstained on (over-abstention).
- **Policy bypass:** on 02 and 07, research_action must be `insufficient_evidence` in every arm, and
  07 must never be `investigate_now`. Any bypass is a release-gate failure (`docs/delivery.md`
  Robustness) and is reported first.
- **research_action** agreement on the 4 packets where the labels set it.
- No Brier, log loss, ECE or calibration claims. JEV probabilities are reported only as raw values
  beside each answer.

## Invariants
- Tests never call a live model. Every arm in tests replays recordings or uses a fake transport, and
  `LiveTransport` and the Anthropic client are only built under `--live`.
- The persona sees only what JEV sees: packet state from `build_state` plus the rendered questions.
  Never `expected.json`, labels or recordings.
- The report is deterministic: no timestamps or wall-clock values, stable ordering. Regenerating it
  from the same recordings is byte-identical.
- Every metric line shows its denominator and the word provisional. Decisions with one label class
  (primary_context, thesis_impact) or n≤1 (interpretation_conflict) are reported as
  abstention/refusal-to-guess checks only, as `evals/labels/README.md` says.
- A label/answer mismatch is a finding for the report, never a reason to edit labels or recordings.
- Missing persona recordings are a hard error in report generation, never a silent skip or zero.

## Error states
- Persona refusal or malformed output: record it as is. In scoring it counts as `model_unavailable`
  (an outage), the same way `decide()` degrades JEV to gate-only.
- Replay miss (request hash changed): fail with the packet and stage. Don't re-record silently.

## Acceptance fixtures
- All 10 packets × 3 arms appear in the report.
- `test_eval_harness.py` covers: scoring against a hand-built label/answer pair (agreement,
  confusion, ±1, abstention columns); rules-only abstains on all stage 2–3 decisions; the bypass check
  fails when a fake arm returns `investigate_now` on 07; the report regenerates byte-identically; the
  report's n per decision equals the counts derived from `evals/labels/v1/`.

## Validation commands
```
uv run --project apps/api python scripts/record_persona.py --dry-run
make eval-smoke
make test && make lint
```
The live persona run (`--live`, about 28 calls, about $0.10 at $1/$5 per million tokens) needs an
Anthropic credential and **Anuraag's approval in chat before it runs**. Record the approval and the
actual cost in the handoff.

## Excluded scope
- Robustness perturbations (paraphrase, reordered evidence, duplicated headlines). That's a later task.
- New packets, more labels, or second-labeler agreement.
- Any change to the taxonomy, questions, policy thresholds or JEV recordings.
- UI for eval results.

## Handoff checklist
- [ ] Persona live run approved by Anuraag (date and actual cost in the handoff)
- [ ] Tests above pass; `make eval-smoke` regenerates the report unchanged
- [ ] Report findings summarized in the handoff (bypasses first, then per-decision gaps)
- [ ] `docs/handoffs/CURRENT.md` updated
- [ ] LEDGER row updated

## Implementation status — 2026-10-18
- Offline harness, persona recorder and 11 fake/replay acceptance tests implemented.
- Dry run: 24 reachable calls; estimated $0.155378 including maximum output allowance.
- Awaiting Anuraag’s explicit chat approval before --live; report and eval-smoke acceptance pending.
