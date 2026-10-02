# T-013 — Contracts v1.1 (valuation, issue, instrument, symbol_mapping, brief additions)

- **Implementer:** Claude Code   **Reviewer:** Codex (testability, producer fit)
- **Branch:** task/T-013-contracts-v1-1   **Depends on:** T-005, T-006, T-007   **Contract version:** v1.1
- **Effort:** default reasoning

## Problem
T-005, T-006 and T-007 each shipped a shape that both lanes depend on, but only as Pydantic models or
web view types. Their handoffs proposed shared schemas and deferred them to one bump. Until those schemas
exist, the API valuation response, the instrument master and the Today issue can drift from what the other
lane expects, and the running brief can't carry the pending sources its view already shows.

## User-visible outcome
None directly. Both lanes validate the valuation response, instrument master, symbol mappings and brief
issues against one canonical JSON Schema each, and tests fail when a producer drifts from the contract.

## Read (only these)
- `docs/decisions/ADR-001-contracts-v1.md`
- `packages/contracts/schemas/`, `packages/contracts/tests/`
- `apps/api/app/models/valuation.py`, `apps/api/app/models/instruments.py` (producers; read-only)
- `apps/web/lib/today/types.ts`, `apps/web/tests/today-fixtures.test.tsx`
- Proposals: handoffs at `cc8f1f5` (valuation), `3e744e2` (issue, pending_sources), `f0caae1` (instrument)

## Owned paths (edit only these)
- `packages/contracts/schemas/`, `packages/contracts/tests/`
- `docs/decisions/ADR-004-contracts-v1-1.md` (new)
- `apps/api/tests/test_contracts_v1_1.py` (new file only; no other API path, so no overlap with T-012)
- `apps/web/fixtures/today/running.json`, `apps/web/tests/today-fixtures.test.tsx`

## Versioning rule
v1.1 is **additive**. It adds new schemas, new `$defs` and optional fields. It adds no new required key to a
v1 schema and narrows no v1 rule, so every v1 document stays valid. The existing v1 examples must still
pass unchanged.

## Schemas
**common** (new `$defs`):
- `date`: `YYYY-MM-DD` pattern plus `format: date`.
- `money_string`: signed, exactly 2 fractional digits.
- `weight_string`: unsigned, exactly 6 fractional digits.
- `unavailable_reason`: the 9 valuation codes.
- `amount`: `{kind: calculation, value: money_string, basis}` or `{kind: unavailable, reason}`.
- `weight_amount`: the same union, with `weight_string` as the value.
- In both, `basis` is a nonempty string. Rounding is the producer's job (half-even, at serialization only).

**valuation** (mirrors `models/valuation.py`):
- Root: required `portfolio_version_id`, `base_currency` (const `USD`), `cutoff`, `positions`, `totals`,
  `coverage`. No extra properties at any level.
- Position: `instrument_id`, `display_symbol` (string or null), `quantity` (positive decimal), `cost_basis`
  (decimal or null), `price` (object or null), `market_value` (amount), `unrealized_pl` (amount) and
  `weight` (weight amount).
  - `price` has `value` (original decimal, not rounded), `observation_id`, `observed_at` and `feed`.
- Totals: `priced_value`, `cash` and `total_value`, each an amount.
- Coverage:
  - `positions`, `priced` and `unpriced` are counts of 0 or more.
  - `by_reason` maps only the 4 market-value reasons (`no_price`, `conflicting_prices`, `unit_mismatch`,
    `currency_out_of_scope`) to counts of at least 1.
- Count and sum agreement, and `price: null` ⇔ an unavailable `market_value`, stay application-level
  (ADR-001, Consequences).

**issue** (the canonical form of the T-007 view `Issue`):
- `id` and `decision_id`: UUIDs.
- `holding`: `{instrument_id, symbol: string|null, name}`.
- `observation`: `{text, source, observed_at}`.
- `interpretation` and `next_question`: nonempty strings.
- `evidence_status`: `supported | partial | contested | insufficient`.
- `exposure`: a weight amount, meaning the holding's share of priced value as computed by T-006, never by a
  model.
- `evidence_ids`: at least 1, unique, free strings (ADR-001).
- The view's resolved `evidence[]` and the display text for exposure and reason are API/web projections,
  not contract fields.

**instrument**: `id` (UUID), `name` (nonempty), `asset_type` (`common_stock | preferred_stock`) and
`currency`. Identity is the UUID, never the symbol.

**symbol_mapping**:
- `symbol` is nonempty, trimmed and contains no ASCII lowercase.
- `instrument_id` is a UUID.
- `valid_from` is a date (inclusive). `valid_to` is a date (exclusive) or null (open-ended).
- `valid_to > valid_from`, foreign keys and the no-overlap rule stay in repository validation.

**brief** (optional additions):
- `coverage.pending_sources`: an array of strings. If it is nonempty, `status` must be `running`.
- `issues`: at most 3 issues.
  - `no_material_change` carries no issues.
  - Each issue's `decision_id` must be in `decision_ids`. JSON Schema can't express that, so the publish
    verifier must check it.

## Not in v1.1 (decided)
- Confirm/readiness and import preview shapes stay OpenAPI-only. Each has one producer and is exported by
  `make contracts`, so a JSON Schema copy would be a second source of truth.
- No `contract_version` field on entities. The version is recorded in ADR-004 and in common's description.
- No codegen, and the Today fixtures don't carry `brief.issues` yet. That needs the weight→text formatter,
  which belongs with the /briefs API web task.

## Acceptance fixtures
- `packages/contracts/tests/gen_examples.py` gets one valid base per new entity and invalid cases that each
  break one rule:
  - Money with 1 decimal place, weight with 2.
  - A float value, and an unknown reason.
  - An unavailable amount that carries a value.
  - An unknown `by_reason` key, or a zero count.
  - A non-USD base, or an offset cutoff.
  - An issue with no evidence, or an issue with a probability-like exposure.
  - A lowercase or untrimmed symbol, or an impossible date.
  - A brief that is pending but not running, or a clean day with issues.
  - A brief with 4 issues.
- Extra valid cases show the rules don't over-reject:
  - An empty portfolio with unknown cash.
  - A negative P/L.
  - An open-ended mapping.
  - A running brief with pending sources.
- `apps/api/tests/test_contracts_v1_1.py` validates, with format checking on:
  - The real `GET /portfolio-versions/{id}/valuation` response for the synthetic portfolio, which includes
    the unpriced SYN03.
  - The empty-portfolio valuation.
  - Every record that `FileInstrumentRepository` loads.
- `running.json` brief gains `pending_sources`. The web fixture test asserts that the view's `pending` ids
  equal the brief's `pending_sources`.

## Validation commands
```
python3 packages/contracts/tests/gen_examples.py && git diff --exit-code packages/contracts/tests/examples
make test
make lint
make contracts && git diff --exit-code packages/contracts
```

## Planned commits
1. `docs:` this spec and the ledger row.
2. `test:` v1.1 examples and entity list. These fail because the schemas don't exist yet.
3. `feat:` v1.1 schemas and ADR-004. Contract tests pass.
4. `test:` API producer conformance, and the web `pending_sources` fixture and assertion.
5. `docs:` handoff and ledger.

## Handoff checklist
- [ ] Tests above pass
- [ ] `docs/handoffs/CURRENT.md` updated
- [ ] LEDGER row updated
