# Handoff — T-006 Deterministic portfolio valuation

- **Updated:** 2026-09-27 by Codex
- **Branch / worktree:** task/T-006-valuation @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews `git diff origin/main...task/T-006-valuation` against
`docs/tasks/T-006-portfolio-valuation.md`, then runs `make test`, `make lint`, and
`make contracts && git diff --exit-code packages/contracts`.

## Done this session
- Created the requested branch from fetched `origin/main` and implemented planned commits 1–4;
  this handoff/ledger update is planned commit 5. The initial specification commit intentionally
  fails collection because the domain module does not yet exist; subsequent implementation passes.
- Added pure Decimal valuation in a local precision-34, half-even context. Both observation and
  receipt times must satisfy the supplied cutoff. Latest conflicting values remain unavailable;
  equal values use the smallest observation UUID. Currency restrictions precede selection.
- Added explicit unavailable amounts, partial coverage, source prices, P/L, priced-value weights,
  cash, and total-value precedence. Calculations remain unquantized until response serialization;
  money uses two places and weights six. Raw quantity/cost strings and null cost basis survive.
- Added injectable portfolio/observation repository protocols and immutable synthetic file-backed
  snapshots. Startup validates complete snapshots and rejects invalid records, unknown version
  references, duplicate positions, non-positive quantities, and duplicate observation IDs.
- Added `GET /portfolio-versions/{id}/valuation?cutoff=...Z` with problem bodies for missing versions,
  previews, unsupported base currency, malformed cutoffs, and pre-confirmation cutoffs.
- Registered the router and regenerated OpenAPI. No fixture or shared JSON-schema edits.
- Added 57 deterministic tests across domain behavior, Decimal precision/rounding, canonical input
  contract compatibility, loaders, dependency injection, startup failure, and API errors.

## Tests run
- Initial domain specification → expected missing-module collection failure (planned commit 1).
- Final targeted valuation suite → 57 passed.
- `make test` → 300 Python tests and 64 Vitest tests passed.
- `make lint` → Ruff check/format, ESLint, Next typegen, and TypeScript passed.
- `make contracts && git diff --exit-code packages/contracts` → passed after generated-file commit.
- `git diff --check origin/main...HEAD` → passed.
- One existing upstream Starlette/AnyIO deprecation warning; no test failures.

## Contract changes proposed (not applied)
Add `valuation.schema.json` at the next shared schema bump, reusing the T-007 Amount/Exposure shape:
- Root: no additional properties; required portfolio_version_id (UUID), base_currency (constant USD),
  cutoff (UTC timestamp), positions (array), totals, coverage.
- Amount: discriminated union of `{kind: calculation, value: decimal-string, basis: nonempty string}`
  and `{kind: unavailable, reason: code}`. Money calculation strings have exactly two fractional
  digits; weight calculation strings have six. Values are rounded half-even only at serialization.
- Reason enum: no_price, conflicting_prices, unit_mismatch, currency_out_of_scope,
  market_value_unavailable, cost_basis_unknown, no_priced_value, cash_unknown, positions_unpriced.
- Position: required instrument_id, display_symbol (string or null if absent in stored position),
  quantity (positive decimal string), cost_basis (decimal string or null), price (object or null),
  market_value, unrealized_pl, weight. Preserve repository position order and original quantity/
  cost_basis strings. Price requires value (original decimal string), observation_id (UUID),
  observed_at (UTC timestamp), and feed (existing feed enum).
- Totals: required priced_value, cash, total_value, each Amount. priced_value is the sum before
  quantization, never the sum of independently rounded position response values.
- Coverage: required nonnegative positions, priced, unpriced counts and by_reason map of positive
  counts, limited to market-value reasons (no_price, conflicting_prices, unit_mismatch,
  currency_out_of_scope). Cross-field count/sum invariants remain application-level.

## Unresolved / assumptions
- Price.value preserves the selected observation's original precision rather than rounding the
  evidence to cents. Computed monetary amounts alone are rounded to cents; weights to six places.
- A unit mismatch retains the selected source price with its observation reference, while market
  value is unavailable. Currency-out-of-scope and missing/conflicting prices expose price null.
- Empty confirmed portfolios have priced_value unavailable/no_priced_value; if USD cash is known,
  total_value is that cash (every position is vacuously priced). An absent display label is null.
- Arithmetic follows the specified precision-34 Decimal context; sums use stable value order so
  position permutations do not affect results at that context's precision boundary.
- Synthetic repositories are process-lifetime snapshots, not durable portfolio persistence. T-011
  still owns confirmation and immutable version storage. No provider calls, FX, freshness judgments,
  live orders, or web UI changes were added.
