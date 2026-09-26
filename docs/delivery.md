# Delivery: tests, release gates, phases, case study (blueprint §19–22)

## Test strategy
- Unit: returns, weights, FX alignment, splits, calendars, timezones, missing values, thresholds.
- Property: value conservation under supported transforms, idempotency, stable ordering.
- Provider contract tests on recorded/synthetic responses; detect schema drift.
- Integration: DB transactions, retries, publication, authorization.
- E2E: the three jobs, incl. a partial brief and a stale intraday feed. Accessibility checks +
  manual keyboard/screen reader.
- Model evals measure decision quality; UI tests can't. Deterministic regression tests never call
  live models.

## Proposed release gates (targets, not results; record n and intervals)
| Gate | Criterion | On failure |
|---|---|---|
| Integrity | all critical arithmetic, tenancy, cutoff tests pass | block release |
| Provenance | every displayed material claim has a valid evidence relation | block artifact |
| Freshness | every stale-feed fixture disables dependent readiness | block release |
| Alert usefulness | ≥80% reviewer precision on highest-priority alerts | retune / narrow |
| Material-event recall | measured vs prespecified labeled set + baseline | investigate missed classes |
| Calibration | match or beat baseline Brier on supported slices | hide numbers / recalibrate |
| Robustness | no critical policy bypass in contradiction + injection fixtures | block release |
| Comprehension | pilot users explain evidence + uncertainty unaided | revise presentation |

Don't buy precision by abstaining on everything — report coverage and recall beside precision.
Bootstrap at event/day level for correlated cases.

Outcome studies: fill at next executable observation after signal availability with explicit spread,
slippage, fees, liquidity, gaps; never same-bar low or assumed intrabar order. Compare to simple
baselines, disclose all variants, report failures and drawdowns.

## Phases (planning range: ~7–13 weeks part-time)
- **0 — Contracts + access (2–4 days):** JEV access, entitlements, scope, source ledger; product,
  evidence, taxonomy, schema specs; ten adversarial packets; fixture-only prototype. Exit: one packet
  traverses the contracts; every critical unknown has an owner.
- **1 — Morning slice (1–2 wks):** auth, CSV review, instrument resolution, portfolio versions,
  valuation, scheduled jobs, Today on fixtures; one price provider + SEC. Exit: reproducible
  import→brief; truthful partial states.
- **2 — JEV judgment (1–2 wks):** adapter, staged taxonomy, packet builder, policy gates, provenance
  verifier, eval harness; first labeled set vs rules-only and persona baselines. Exit: supported
  decisions meet provisional gates; unsupported slices abstain.
- **3 — Discovery + volatile-day (1–2 wks):** filters, ranking, stock detail, exposure comparison,
  timelines, conditional plans, thesis versioning, counterevidence. Exit: all three jobs on known
  scenarios incl. missing/conflicting data.
- **4 — Shadow pilot (2–4 wks observation):** scheduled briefs, no live execution; track latency,
  cost, outages, calibration drift, comprehension; weekly failure review.
- **5 — Extend + case study:** analogues, paper simulation, wider coverage only when justified; demo,
  architecture diagram, annotated UX, eval report, honest limitations.

Weekend scope: fixture import, Today page, one investigation, small JEV experiment if access,
preliminary eval report. Cannot establish expert-level reliability.
Critical path: provider access → canonical snapshots → evidence packets → taxonomy eval → dependable
publication. Frontend proceeds against fixtures in parallel.

## Case study (§22)
Question: can an evidence-first AI system help active investors prepare better decisions without
presenting uncertain judgments as certainty?
Narrative: fragmented morning routine → three jobs → UX evolution (dashboards → concise brief with
progressive disclosure; why confidence %, alert volume, buy/sell labels failed) → how the
seasoned-trader principle became executable → one fully traced event from raw observation to UI.
Collect as you go: dated specs, design alternatives, consented interview notes, test results, ADRs,
failure cases, pre-tuning baselines, frozen eval split, and `docs/handoffs/case-study-log.md`.
Results: task time, comprehension, top-alert precision, event recall, abstention coverage,
calibration, reliability, cost — each with denominator, timeframe, baseline, uncertainty. Blank until
measured. "Implemented a replay harness" is engineering; "improved decisions" needs a study; "beat the
market" isn't claimable from this demo.
Demo: synthetic portfolio with one mapping error → fix → brief → supported event + contradictory
source → weak-fit discovery candidate → volatile-day plan that includes waiting → replay a correction
that changes a thesis state. Strongest moment: the system declining an unsupported conclusion.
