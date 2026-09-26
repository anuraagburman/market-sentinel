# Decision system: JEV judgment, evidence, calibration (blueprint §6–10, §18)

## The design standard
JEV must behave like a seasoned trader/analyst **because the system encodes disciplined judgment** —
taxonomy, evidence standards, calibration, regime awareness, evaluation. A prompt saying "act like
an expert trader" does **not** satisfy this. If a distinction appears only in prose (not in taxonomy,
fixtures and policy tests), it is not implemented.

A seasoned analyst asks: is it new, material, credible, already reflected in price, relevant to the
holding period, consistent with market context? They seek contrary evidence, separate facts from
explanations, and accept that the right answer may be to wait.

## Division of responsibility
Code: returns, weights, concentration, time alignment, freshness. Retrieval: evidence. Generative
model: extract claims, draft explanations. JEV: bounded judgments against a defined state + rubric.
Deterministic policy: combine judgments into priorities and abstention. User: decides.

TypeSafe JEV documents Choice, Score, and Null primitives [S1: https://docs.typesafe.ai/introduction].
Questions in one call are evaluated independently against the same state → dependent decisions need
staged calls with validated intermediate results. Typed output ≠ factual correctness or expertise;
validate on our own task distribution. Don't assume project-specific fine-tuning; build adapter +
eval loop first.

## Decision design record (per classifier question)
owner, purpose, allowed outputs, horizon, evidence requirements, positive/negative examples,
ambiguity policy, calibration target, version. Stored beside code and fixtures. A taxonomy change
is a behavior change → evaluation + release review.

## Expert behaviors that must exist as fixtures + policy tests
- Earnings miss without comparable expectations ≠ automatic negative surprise.
- Large fall right after a split may be a normalization error.
- Ten syndicated articles may be one source.
- A good company can be a poor short-horizon setup.
- A true catalyst can coexist with an uncertain price response.
- High-confidence classification is suppressed when its input is stale.

## Decision taxonomy (proposed; JEV does not ship financial labels)
Separate decisions where several conditions can be true; exclusive Choice only for exclusive outcomes.

| Decision | Outputs | Required context |
|---|---|---|
| data_usability | usable, partial, unusable | freshness, feed, session, missing fields |
| event_family | earnings, guidance, corporate_action, regulatory, macro, other, unknown | verified event metadata |
| primary_context | company, sector, market, mixed, unknown | residual move and evidence |
| novelty | new, update, repeated, unclear | previous event and source lineage |
| evidence_sufficiency | sufficient, partial, insufficient | claim-level support and contradictions |
| thesis_impact | strengthens, weakens, invalidates, unrelated, unclear | original claim and horizon |
| research_relevance | ordinal 1–5 | materiality, exposure, horizon |
| interpretation_conflict | yes / no | competing supported explanations |

Rubric for research_relevance: 1 = no demonstrated connection to portfolio or research intent;
3 = plausible connection needing more evidence; 5 = verified material event directly affecting a
holding or stated objective. Intermediate levels need worked examples. Ordinal ≠ probability or
expected return.

"mixed" = supported multi-driver; "unknown" = unresolved attribution. "No catalyst found" is a
coverage statement. "Priced in" is a cautious judgment backed by timing, expectations and price
history — never inferred from a muted reaction.

## Policy precedence
1. Deterministic integrity checks. Unusable → abstain. Partial → only claims supported by available
   inputs; dependent conclusions disabled.
2. Classify evidence and event context.
3. Portfolio relevance and thesis impact.
4. Rank eligible investigations with a versioned policy.

Priority index = explicit weights over exposure, materiality, time sensitivity, relevance. Call it a
**priority index**, not confidence. Never multiply JEV probabilities as if independent.

Output actions: **investigate_now, review_today, watch_condition, no_new_material_issue,
insufficient_evidence** — research actions only. Policy can flag user position-limit breaches
deterministically. JEV cannot waive a hard constraint or promote an unusable event.

## Evidence
Hierarchy: official filings, company releases, authoritative economic releases → what was reported.
Licensed news → independent context. Analyst opinion → attributed interpretation. Social → lead only.
Authority is claim-specific (a company is authoritative on its guidance, not on its future). An
excerpt must actually support its linked claim.

### Evidence packet
event identity, instrument identity, observation cutoff, normalized metrics, supporting claims,
counterclaims, unresolved questions, source lineage, timestamps (publication **and**
first-known-to-system), coverage gaps. Corrections keep the original + attach the correction.
Deduplicate syndication by canonical story + content similarity; count independent originators, not
URLs. Store minimal licensed excerpts + hashes when retention is restricted. Retrieval honors tenant
permissions and licenses **before** anything enters a model request.

### Regime
Separate observable dimensions: trend, realized volatility, breadth (if available), liquidity,
scheduled event intensity — trailing data at cutoff, with lookbacks, thresholds, missingness.
Transparent rules first; ambiguous → mixed/unknown. Regime changes base rates, evidence requirements
and eval cohorts; it doesn't prove returns. Never substitute an AI narrative for measured context.

### Freshness
Per source and use case. Illustrative: intraday tolerance 60s for an entitled live feed (measure
first). 15-min delayed feed always says delayed and can't pass that gate. Morning briefs may use
previous close with explicit session labels. Distinct policies for holidays, half days, DST, halts,
extended hours. Never compare partial-session volume to full-session averages without normalizing.

## Calibration and evaluation
- A catalyst-support judgment estimates whether an evidence relation meets a rubric — not trade
  profit. Store raw outputs, calibrated values, method, validation sample. Provider confidence ≠
  class probability.
- UI shows states (Supported / Mixed / Insufficient) first; numbers only when target + validation
  are clear. Unvalidated numbers stay internal.
- Eval set: 60–100 curated dev cases → ≥500 labeled packets (earnings, macro shocks, quiet days,
  contradictory news, corporate actions, missing data). Deliberately sample rare classes.
- Labels by an experienced practitioner with written rubrics; independent second label on a subset;
  adjudicate. Otherwise call labels **provisional**. Separate as-of judgment from later returns.
- Leakage: chronological splits; group related stories/issuer events/near-duplicates; fit thresholds
  and calibrators on train/val only; untouched later test period; purge + embargo overlapping
  forward-return labels. Replay only info known at cutoff (amended filings, revised macro, restated
  fundamentals, today's constituents all leak). Frozen archives can't remove model memorization →
  prospective shadow evaluation.
- Report: per-class precision/recall, confusion matrices, abstention coverage, error rate among
  non-abstained, by regime and horizon; Brier, log loss, reliability plots with counts; ECE only with
  binning + intervals.
- **Baselines on the same packets:** rules-only vs generic expert-persona prompt vs engineered JEV.
  Robustness: paraphrases, reordered evidence, missing-source perturbation, duplicated headlines.

## Scenarios and decision support
Conditional scenarios: what must happen, supporting observations, invalidation, exposed holdings.
Narrative ≠ forecast; no scenario probabilities without a prediction target and validation.
Analogues optional: match on pre-event features, horizon, liquidity, catalyst, regime; report n,
selection, dispersion, adverse outcomes.

Volatile-day plan example: guidance cut before a macro release, stock and sector down → accumulate
condition (issue temporary), reduce condition (thesis invalidated), wait condition (liquidity/info).
Every condition needs observable evidence. **Model-supplied price levels are prohibited**; prices come
from dated calculations or the user.

Sizing: code may compute an illustrative paper quantity from user risk budget and entry→invalidation
distance; state gaps/slippage can exceed it; cap by paper cash and concentration. Never infer risk
tolerance from frequency or age. Distinguish thesis change from constraint breach.

Decision journal: thesis, evidence snapshot, policy version, horizon, action, reason. Outcome review
compares expectations to events; decision quality and market outcome reviewed separately.

## Taxonomy spec format (example)
```yaml
id: catalyst_support
version: 1
purpose: Judge support for the stated catalyst hypothesis
horizon: explicit_in_packet
outputs: [supported, mixed, insufficient]
required: [timestamped_event, source_linked_claims, counterevidence_search_status]
rules:
  - Repeated stories are not independent corroboration
  - A price move alone does not establish its cause
  - Missing evidence is not negative evidence
  - Evaluate only information known at the cutoff
abstain_when: [critical_source_missing, timestamp_order_invalid, instrument_identity_unresolved]
```
The JEV adapter translates this into verified provider syntax. Fixtures per rule incl. borderline and
conflicting cases. Policy thresholds live in a separate versioned file.

Extraction contract: claim text, source span, entity, metric, period, units, publication time; never
fill missing values from model memory. Explanation contract: consumes approved claim ids + decision
fields, returns concise text with claim refs, labels interpretation. Verifier rejects new numbers or
unsupported causal certainty.
