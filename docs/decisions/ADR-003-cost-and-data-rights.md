# ADR-003 — Spend ceiling, providers, and data rights

- **Status:** accepted (Anuraag, 2026-09-27)
- **Date:** 2026-09-27
- **Task:** T-000

## Context
The pilot is a single-user research tool, so cost should stay minimal. The swing/multiweek horizons
(ADR-002) need only end-of-day data. Provider terms decide what can be shown publicly.

## Decision
1. **Ceiling:** $0/month for data; hard cap of **$25/month for model calls**, with an alert at 80%.
2. **When the cap is reached,** model stages stop for the rest of the month. Briefs still publish
   the deterministic parts (valuation, filings, calendar) as a visible partial state whose coverage
   names the skipped stage. Nothing is filled in by guesswork.
3. **Model calls only where they add judgment:** JEV and explanations run only for holdings or
   candidates that trigger a deterministic candidate issue. Never for arithmetic (project rules).
4. **Providers (free tiers):**

   | Need | Provider | Plan |
   |---|---|---|
   | Daily closes | Alpaca Market Data | Free plan: historical daily bars from the SIP (consolidated) feed. `feed` is stored on every observation. |
   | Filings, events | SEC EDGAR | Free; requests carry a declared User-Agent contact string; respect SEC rate limits |
   | Macro, rates | FRED | Free API key |
   | Fundamentals, calendar | Financial Modeling Prep | Free tier; upgrade only if coverage is measurably too thin |
   | News | none | Deferred until rights are confirmed (T-000) |

   Plan terms and prices were not verified at the time of this decision. Check them at signup and
   amend this ADR if they differ.
5. **Data rights:** private, single-user use only.
   - Models may process public-domain data (SEC, FRED) directly. Vendor market data reaches a model
     only as derived numbers (returns, weights, ranges), never as raw feed output.
   - Screenshots, demos, the case study and anything in Git use **synthetic fixtures only**. Real
     vendor data and real holdings never appear publicly.
   - Multi-user or public delivery requires a new licence review before release (T-000 open item).

## Consequences
- T-008 targets Alpaca free, SEC and FRED first; FMP is optional.
- The run pipeline needs a per-month spend meter and a "stage skipped: budget" coverage reason.
- An upgrade (e.g. Alpaca's paid real-time SIP plan) needs a new ADR with the reason.

## Open
JEV / TypeSafe pricing is unknown and not yet inside the $25 cap. Record it when access is confirmed.
