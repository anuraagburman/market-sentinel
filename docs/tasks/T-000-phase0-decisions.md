# T-000 — Phase 0 decisions and access

- **Owner:** Anuraag (Claude Code can draft ADRs from your answers)   **Effort:** your time, not tokens

Phase 0 exits when one packet can traverse the contracts and every critical unknown has an owner
(blueprint §20). These need a human answer; agents shouldn't guess them.

## Access (blocking)
- [x] (2026-09-27; key in `~/.config/market-sentinel/.env`, pricing still open) JEV / TypeSafe account and API access confirmed → unblocks T-009
- [x] (2026-10-02; free Basic plan, `ALPACA_DATA_FEED=sip`, SIP daily bars verified) Alpaca market-data account; feed chosen and stored explicitly (IEX vs SIP) → T-008
- [x] (2026-10-02; `SEC_USER_AGENT`, submissions endpoint verified) SEC EDGAR: User-Agent contact string per SEC access guidance → T-008
- [ ] Fundamentals/calendar provider (e.g. Financial Modeling Prep) plan + endpoints checked
- [x] (2026-10-02; `FRED_API_KEY`, DGS10 verified) FRED API key

Keys live in `~/.config/market-sentinel/.env` (outside Git) as `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`,
`ALPACA_DATA_FEED`, `SEC_USER_AGENT`, `FRED_API_KEY`. All three providers are on free tiers.
- [ ] News provider: deferred until coverage, timeliness, model-processing and retention rights are confirmed

## Decisions (record each as an ADR in `docs/decisions/`)
- [x] (ADR-002) Supported universe and horizons; explicit exclusions (default: liquid US common equities +
      benchmark ETFs; swing/multiweek)
- [x] (ADR-003; multi-user review still open) Data rights: private use, model processing, public screenshots, later multi-user delivery
- [x] (ADR-005; practitioner still open) Who reviews taxonomy labels (qualified practitioner?) — else labels are "provisional"
- [x] (ADR-003; JEV cost still open) Monthly spend ceiling (data + model) and which enrichments are optional
- [x] (ADR-002) Briefing time and timezone policy (you're outside US market hours)
- [x] (ADR-005) Retention: holdings, evidence, journals, raw model outputs
- [ ] What needs product/jurisdictional review before any public release

## Also this phase
- [ ] Five to eight investor interviews scheduled (blueprint §5) — can run in parallel with builds
