# Provisional labels — v1

One file per fixture packet in `v1/`, giving an answer or a reasoned abstention for every taxonomy v1
decision (`decisions/taxonomy/v1.yaml`). These are the ground truth T-010 scores against.

- **Status:** every label is `provisional` (ADR-005). No practitioner has reviewed them, and there is
  no second labeler. Every metric that depends on them is provisional too.
- **Labeler of record:** Anuraag, who approved all 10 packets on 2026-10-18. Claude Code drafted them.
- **Blind:** labels were drafted without reading `evals/recordings/`, recorded JEV answers or
  policy-engine output. Relabeling must be blind too.
- **Tied to the frozen packet:** `packet_hash` equals `event.json`'s hash. If a fixture is
  regenerated, `evals/tests/test_labels.py` fails and the labels must be checked again.

## Procedure
1. Read the packet's event, evidence, claims, observations and expected files. Judge only what was
   known at the cutoff, and never use evidence that `expected.json` excludes (08's ev-2, 09's ev-1).
2. Answer each decision from its `outputs`, or abstain with a reason from its `abstain_when`.
   When `data_usability` is `unusable`, every stage 2–3 decision abstains with `unusable_input`.
3. When the packet can't support a confident answer, use the decision's `ambiguity_policy`.
   Never guess.
4. Write a one-line `why` naming the packet field or evidence id it relies on.
5. Add `research_action` only when a label trips a hard gate in `decisions/policies/v1.yaml`
   (`unusable` or `insufficient`). Otherwise the packet doesn't determine the action.
6. Anuraag approves every label. A rejected label takes Anuraag's value and reason.

## Rubric (rules Anuraag decided on 2026-10-18, applied to every packet)
| Decision | Rule |
|---|---|
| data_usability | `partial` when a field used downstream is missing: a stated coverage gap, no observations, a stale close, or a single close with no prior close (so no move can be computed). `usable` needs fresh closes on both sides of the event and no gaps. |
| event_family | Take it from `event.event_type`, the packet's verified metadata, and check it against the evidence. |
| primary_context | `unknown` on every packet: none has benchmark or sector moves, and a price move alone does not establish its cause. |
| novelty | `unclear` by default, because no packet has `previous_events`. Use `repeated` only when the packet itself shows syndication (03) and `update` only for a `correction_of` (09). |
| evidence_sufficiency | No packet records a counterevidence search, so the best possible answer is `partial`. `insufficient` when the stated catalyst is unsupported (01's "miss" with no consensus figure) or there is no catalyst (05). Abstain `critical_source_missing` when the source that would carry the event failed (10). |
| thesis_impact | Abstain `no_recorded_thesis` on every packet. |
| research_relevance | Every event instrument is a holding, and no packet verifies materiality, so nothing scores 5 (round down). 4 = a verified company event; 3 = a contested or single-originator event; 2 = no corporate event (a feed outage or coverage failure). |
| interpretation_conflict | `yes` only when independent sources each support a competing explanation (06). Everywhere else, abstain `counterevidence_search_incomplete`, because `no` needs a completed search. |

## Counts (T-010 denominators, n=10)
| Decision | Values | Abstentions |
|---|---|---|
| data_usability | usable 1, partial 7, unusable 2 | 0 |
| event_family | earnings 3, other 3, regulatory 1, guidance 1 | unusable_input 2 |
| primary_context | unknown 8 | unusable_input 2 |
| novelty | unclear 6, repeated 1, update 1 | unusable_input 2 |
| evidence_sufficiency | partial 5, insufficient 2 | unusable_input 2, critical_source_missing 1 |
| thesis_impact | — | unusable_input 2, no_recorded_thesis 8 |
| research_relevance | 4: 4, 3: 2, 2: 2 | unusable_input 2 |
| interpretation_conflict | yes 1 | unusable_input 2, counterevidence_search_incomplete 7 |

`research_action` is set on 4 packets, all `insufficient_evidence`: the unusable gate on 02 and 07,
and the insufficient-evidence gate on 01 and 05.

Known limits: primary_context and thesis_impact each have only one answer, and interpretation_conflict
has one non-abstained case. On those decisions T-010 can only check abstention and refusal to guess,
not discrimination between classes.
