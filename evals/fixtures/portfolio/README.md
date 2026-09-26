# Synthetic import

All symbols and issuers (Synthela 01–19) are fictional. Values are invented USD
amounts, not market quotes. CSV cost_basis is total cost, not per-share cost.
T-004 owns the final CSV interface.

There are exactly 20 raw rows (excluding the header) and 19 confirmed positions.
The accidental duplicate is removed, not aggregated; no position is invented to
restore a count of 20. Row numbers below exclude the header.

| Case | Raw row | Confirmed resolution |
|---|---|---|
| duplicate row | 20 repeats row 1, SYN01 | User removes row 20; quantity remains 10 |
| ambiguous symbol | 2, SYN-AMB | User selects fictional Synthela 02 (SYN02), rather than Synthela 02 Preferred |
| missing price | 3, SYN03 | Position retained; no observation exists; value remains unknown |
| missing cost basis | 4, SYN04, empty cost_basis | Required cost_basis remains null |
| mapping error | 5, SYN-TYPO | User fixes mistyped symbol to fictional Synthela 05 (SYN05) |

Instrument IDs end in their issuer number; labels are not identity. Cash is absent
(unknown). Prices are regular-session closing observations at the frozen cutoff.
Quantities, total costs, and prices vary to expose field swaps and row mix-ups.
SYN02 has a fractional quantity (2.5); SYN01 closes above 500 (625.50) and
accounts for more than 20% of priced value; SYN05 closes below 5 (3.25).
No holdings arithmetic or valuation output is supplied.
