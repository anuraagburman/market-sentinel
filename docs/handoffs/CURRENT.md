# Handoff — T-006 Deterministic portfolio valuation

- **Updated:** 2026-09-27 by Codex
- **Branch / worktree:** task/T-006-valuation @ ~/code/ms-wt/api
- **Status:** ready_to_merge

## Next step (exact — the next agent starts here)
Claude Code verifies the requested unit-mismatch review fix, then merges
`task/T-006-valuation` into `main` with `--no-ff` and pushes `main`.

## Done this session
- Applied the sole requested T-006 review fix: a selected observation whose unit differs from
  the position currency now yields price null and unavailable/unit_mismatch.
- Updated `test_currency_reasons` to assert `row.price is None` for both unit mismatch and
  currency-out-of-scope cases.
- Corrected the previous handoff's unit-mismatch assumption and updated the ledger for merge.

## Tests run
- `make test` → 300 Python tests and 64 Vitest tests passed.
- `make lint` → Ruff check/format, ESLint, Next typegen, and TypeScript passed.
- `git diff --check` → passed.
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
- Unit mismatch, currency-out-of-scope, and missing/conflicting prices all expose price null.
  The review correction resolves the earlier unit-mismatch interpretation; no new assumptions.
- Empty confirmed portfolios have priced_value unavailable/no_priced_value; if USD cash is known,
  total_value is that cash (every position is vacuously priced). An absent display label is null.
- Arithmetic follows the specified precision-34 Decimal context; sums use stable value order so
  position permutations do not affect results at that context's precision boundary.
- Synthetic repositories are process-lifetime snapshots, not durable portfolio persistence. T-011
  still owns confirmation and immutable version storage. No provider calls, FX, freshness judgments,
  live orders, or web UI changes were added.
