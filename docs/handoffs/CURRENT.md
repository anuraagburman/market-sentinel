# Handoff — T-008 provider adapters implemented

- **Updated:** 2026-10-17 by Codex
- **Branch / worktree:** task/T-008-provider-adapters @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code: review T-008's owned-path diff against origin/main, starting with
`apps/api/app/providers/{transport,alpaca,sec}.py` and `apps/api/tests/test_providers.py`.
All implementation steps are committed. No live API wiring or persistence was introduced.

## Done this session
- TDD: 24 new non-positive domain/HTTP conformance cases failed before the guard;
  the guard now rejects any non-positive latest candidate without older/tied-positive fallback.
  Removed the original strict xfail; positive prices, negative P/L and zero cash still pass.
- Added injected bounded transport: Decimal JSON parsing, 10-second request timeout,
  3 attempts, 100 pages and 60-second call budget, bounded jitter/backoff, Retry-After,
  redacted typed failures, no credential-forwarding redirects, shared SEC 5 requests/second limiter.
- Added Alpaca daily-bar normalization with calendar-derived NY session closes, effective-dated
  symbols, explicit feed, canonical unadjusted observations, deterministic IDs and visible gaps.
- Added SEC recent/historical metadata normalization, typed Filing/Evidence, accession-based
  sources, safe document URLs, source-record hashes and receipt/cutoff exclusions.
- Synthetic provider wire fixtures use `.payload` JSON, because the existing eval gate reserves
  `.json` for canonical entities. Outputs are schema-validated with format checking in provider tests.
- No credentials loaded, live endpoints called, dependencies added or shared contracts changed.

## Tests run
- Targeted pytest (providers, valuation, valuation API, contracts v1.1) → 124 passed.
- `env -u DATABASE_URL make test` → 466 Python passed, 50 Postgres skipped (no
  TEST_DATABASE_URL configured); 64 web passed. Existing Starlette deprecation warning only.
- `make lint` → passed (Ruff, ESLint, TypeScript).
- `make contracts && git diff --exit-code packages/contracts` → passed, unchanged.
- `git diff --check` → passed.
- First full run caught wire fixtures being treated as canonical schemas; corrected file suffixes
  and reran the full suite successfully. A socket-timeout regression also failed before its fix.

## Contract changes proposed (not applied)
- None for T-008; existing v1.1 remains strict.
- Carry-forward optional v1.2: anchor remaining v1 patterns to reject trailing newlines in Python.

## Unresolved / assumptions
- Inputs are explicitly bounded to at most 366 calendar days per adapter call. No network or
  credential loading occurs at import. Callers supply the client, UTC clock, sleeper, jitter,
  keys/contact and identity mappings. No live smoke was performed.
- Alpaca `adjustment=raw` maps to canonical `none`; `asof=-` disables automatic vendor ticker
  remapping. The local mapping uses inclusive valid_from / exclusive valid_to. Daily bucket
  dates are resolved in America/New_York; observed_at is the calendar close, not bucket time.
  Feed is never substituted. Daily volume follows vendor aggregation and can include extended
  hours; it must not be interpreted as regular-hours-only volume for later liquidity policy.
- Observation IDs use UUIDv5 over sorted compact ASCII JSON of instrument_id, metric, feed,
  session, date, adjustment, observed_at and normalized value. Fractional trailing zeros are
  removed without Decimal context rounding. Receipt time is excluded from identity.
- SEC normalized source/hash input is exactly the sorted compact ASCII JSON object with keys
  cik (10 digits), accession, form, filing_date (ISO date), accepted_at (UTC ISO timestamp),
  primary_document. SHA-256 hashes its UTF-8 bytes; UUIDv5 identity uses the same serialization.
  Receipt time is excluded. published_at is explicit acceptance time; known_at is actual page
  retrieval time. Missing acceptance is an error, never inferred from filing date. License tag:
  `public-domain:sec-edgar`. Same-accession changed metadata produces a new ID/hash; distinct
  amendment accessions remain separate sources. No correction linkage is inferred.
- Covered sessions describe returned records even if a later page fails; complete remains false
  on errors, exclusions or missing sessions. SEC covered date bounds require complete traversal.
  Empty successful SEC coverage means no filings in range, never no material change.
- Single-process limiter is insufficient for multiple ingestion workers; deployment-wide coordination
  remains required before fan-out. No persistence, scheduling or running-API switch is included.
- Official documentation checked this session:
  - Alpaca bars: https://docs.alpaca.markets/us/reference/stockbars
    (1Day, explicit feed/raw adjustment, asof, inclusive bounds and next_page_token).
  - Alpaca FAQ: https://docs.alpaca.markets/us/docs/market-data-faq
    (NY daily buckets, daily condition rules, feed entitlements/403 and recent SIP restrictions).
  - Alpaca calendar: https://docs.alpaca.markets/us/v1.1/reference/getcalendar-1
    (paper-api /v2/calendar, specific closes including early closures).
  - SEC APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
    (10-digit CIK submissions, compact arrays and historical files/date ranges).
  - SEC access: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
    (declared User-Agent, archive URLs, fair access).
  - SEC developer guidance: https://www.sec.gov/about/developer-resources
    (10 requests/second maximum; adapter deliberately uses 5).
- T-012 follow-ups (no task yet; fold them into the next api-lane store task):
  - UNIQUE on `import_confirmations.portfolio_version_id`.
  - Composite (`tenant_id`, `previous_version_id`) FK.
  - `seed_fixture` refuses when a tenant head already exists. Today it chains the fixture on top of real data.
  - Prune `InMemoryPreviewRepository._locks`.
  - `PostgresPreviewRepository.write` picks insert or update implicitly and doesn't check that the update hit a
    row. Use an explicit upsert or assert `rowcount == 1`.
  - `.env.example` defaults `MS_ENV=dev`, which weakens the seed guard if the file is copied as-is.
- Running tests with a dev `DATABASE_URL` exported in your shell fails by design. Unset it or point it at a
  `_test` database. Codex's review run skipped the 50 Postgres tests because no `TEST_DATABASE_URL` was set.
- Carry forward: /briefs projection formatter (Today fixtures with `brief.issues`), codegen, upload size limit,
  per-tenant keys, observation persistence, web grouping of `row_has_errors` + `row_unresolved`.
