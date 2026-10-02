# ADR-004 — Contracts v1.1: additive bump for valuation, issue and instrument data

- **Status:** proposed (awaiting Codex review on `task/T-013-contracts-v1-1`)
- **Date:** 2026-10-02
- **Task:** T-013

## Context
T-005 (instrument master), T-006 (valuation) and T-007 (Today issue) each shipped a shape that both lanes
read, but only as Pydantic models or web view types. Their handoffs proposed shared schemas and deferred them
to one bump, so each producer could drift from what the other lane expects.

## Decision
1. **Minor bumps are additive.** v1.1 adds schemas, `$defs` and optional fields only. It adds no required key
   to a v1 schema and narrows no v1 rule, so every valid v1 document stays valid. A change that breaks this
   is a major bump with its own ADR.
2. **New schemas:**
   - `valuation`
   - `issue`
   - `instrument`
   - `symbol_mapping`
3. **New `common` defs:**
   - `date`
   - `money_string` (2 places)
   - `weight_string` (a 6-place fraction)
   - `unavailable_reason`
   - `amount` and `weight_amount`
4. **Computed values use one tagged shape.** A computed value is either `{kind: calculation, value, basis}` or
   `{kind: unavailable, reason}`. Missing is a reason code, never zero and never free text. Producers round
   half-even only when serializing. Evidence values (`price.value`, `quantity`, `cost_basis`) keep their
   original strings.
5. **An Issue's `exposure` is the T-006 weight**, a fraction of priced value. Display text (for example
   "48.8% of priced portfolio value") and resolved evidence items are projections the web or API builds, not
   contract fields. Issue ids are UUIDs, like every other entity id (ADR-001).
6. **The brief gains optional `issues` (at most 3) and `coverage.pending_sources`.** A nonempty
   `pending_sources` requires `running`, and `no_material_change` carries no issues. An `if` on an optional
   key must `require` that key; otherwise the rule fires on every document that omits it.
7. **Confirm, readiness and import-preview shapes stay OpenAPI-only.** Each has one producer and is exported
   by `make contracts`, so a JSON Schema copy would be a second source of truth.
8. **No per-entity `contract_version` field.** The version lives here and in `common`'s description.
   `decision.schema_version` is unchanged.

## Consequences
- Producers are tested against the schema rather than generated from it. The API test validates real
  valuation responses and the loaded instrument master, with format checking on.
- These rules stay at the application level because JSON Schema can't express them:
  - Valuation counts and sums agree, and `price: null` ⇔ an unavailable `market_value`.
  - Mapping foreign keys, `valid_to > valid_from`, and no overlapping intervals.
  - Each issue's `decision_id` appears in the brief's `decision_ids`.
- `price.value` must be positive. A zero or negative close from a provider now violates the contract, which
  matches the T-008 note that adapters reject non-positive closes.

## Deferred
- Today fixtures carrying `brief.issues`. This needs a weight→text formatter and belongs with the /briefs web
  task.
- Pydantic and TS codegen.
- Per-tenant instrument overrides.
