# ADR-002 — Supported universe, horizons, currency, and briefing schedule

- **Status:** accepted (Anuraag, 2026-09-27)
- **Date:** 2026-09-27
- **Task:** T-000

## Context
T-006 (valuation) and T-008 (provider adapters) need a fixed scope before they can be specified.
`docs/product.md` "Initial decisions" gave defaults; this ADR makes them concrete.

## Decision
1. **Research universe:** US-listed common stocks and ADRs with last close ≥ $5 and 20-session
   average daily dollar volume ≥ $10M, plus benchmark ETFs: SPY, QQQ, IWM, DIA and the eleven
   Select Sector SPDRs. **Excluded:** OTC, SPACs, leveraged or inverse ETFs, preferreds, options,
   other derivatives.
2. **The universe limits research, not valuation.** Discovery candidates and JEV decisions are
   produced only for in-universe instruments. A holding outside it (e.g. a $3 stock) is still
   valued and listed, marked "outside research coverage". It never gets a fabricated judgment.
3. **Horizons:** `swing` = a few sessions to 2 weeks; `multiweek` = 2–8 weeks. Intraday stays
   excluded (reaffirms ADR-001 §8).
4. **Currency:** USD only. A position or price in any other currency is **not valued**, is left out of
   totals, and carries the reason `currency_out_of_scope`. No FX conversion, so no FX provider.
5. **Valuation price:** the latest regular-session (or half-day) close, unadjusted, whose
   `observed_at` and `received_at` are both at or before the valuation cutoff. Freshness judgments
   ("is this close stale?") belong to policy code, not to valuation.
6. **Briefing schedule:** 07:00 in the user's configured IANA timezone (a per-user preference; the
   pilot user sets theirs). The brief covers the latest **completed** US regular session per the
   exchange calendar.
7. **No-session days:** when no US session completed since the previous brief (weekends, NYSE
   holidays), no brief is generated. Today keeps the last brief, labelled as not current.

## Consequences
- T-006 needs no FX or calendar code: it takes a cutoff and returns what is and isn't valued.
- T-008 needs only daily bars and reference data for the universe above; no intraday feed.
- The scheduler (later task) needs an NYSE calendar and a per-user timezone preference.
- Liquidity thresholds are research-coverage defaults, not quality scores; revisit after T-010.

## Deferred
Non-USD instruments and FX · intraday · universe liquidity recalculation cadence (T-008).
