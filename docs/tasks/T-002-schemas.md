# T-002 — Core schemas and decision envelope

- **Implementer:** Claude Code   **Reviewer:** Codex (testability, ambiguity)
- **Branch:** task/T-002-schemas   **Depends on:** — (can start before T-001 merges)
- **Effort:** high reasoning — this is the contract both lanes build on

## Problem
Web and API lanes can't split until the shared shapes exist. Blueprint §14 lists the entities and
invariants; nothing is written as a machine-checkable contract yet.

## User-visible outcome
JSON Schemas for each canonical entity and the decision envelope, plus a taxonomy v1 file,
that fixtures and both apps validate against.

## Read (only these)
- `docs/architecture.md` — "Canonical schemas and invariants"
- `docs/evidence-policy.md` — "Decision taxonomy", "Evidence packet", "Taxonomy spec format"
- `docs/project-rules.md`

## Owned paths
`packages/contracts/schemas/`, `decisions/taxonomy/v1.yaml`, `decisions/policies/v1.yaml`
(skeleton), `docs/decisions/ADR-001-contracts-v1.md`, `packages/contracts/tests/`.

## Scope
- JSON Schema (draft 2020-12) for: PortfolioVersion, Position, Observation, Evidence, Claim,
  Event, Decision (envelope), Brief, Plan, Run; plus the shared `SurfaceStatus` enum
  (ready, running, partial, stale, failed, no_material_change).
- Money/quantities as decimal strings; timestamps UTC ISO-8601; ids UUID; `cost_basis` nullable.
- `taxonomy/v1.yaml`: the eight decisions from the taxonomy table, each with the §6 decision
  design record fields (owner, purpose, outputs, horizon, evidence requirements, ambiguity policy,
  abstain_when, version). Examples may be placeholders marked `TODO(label)`.
- A tiny schema test: one valid and one invalid example per entity.

## Invariants
- Distinct `observed_at`, `published_at`, `known_at`.
- Research actions are exactly: investigate_now, review_today, watch_condition,
  no_new_material_issue, insufficient_evidence.
- No field implies trade-profit probability.

## Validation commands
```
# until T-001 lands:
python3 -m pytest packages/contracts/tests -q
```

## Excluded scope
Pydantic/TS code generation (follow-up once T-001 merges), DB tables, JEV vendor syntax.

## Handoff checklist
- [ ] Schema tests pass
- [ ] ADR-001 written
- [ ] `docs/handoffs/CURRENT.md` + LEDGER updated
