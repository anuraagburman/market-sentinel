# T-008 — Provider adapters (Alpaca daily bars, SEC EDGAR)

- **Implementer:** Codex   **Reviewer:** Claude Code
- **Branch:** task/T-008-provider-adapters   **Depends on:** T-000 access (verified), T-002, T-005, T-006, T-013   **Contract version:** v1.1 unchanged
- **Effort:** default reasoning

## Problem
Valuation still reads synthetic observations. There is no bounded, replaceable provider boundary for
prices or filings. The valuation producer also accepts zero and negative closes despite the positive
price rule in ADR-004; two strict xfails track that gap. This task supplies fixture-tested adapters and
closes the producer gap without loosening the schema.

## User-visible outcome
An ingestion caller can obtain normalized daily closes and filing evidence with provenance and explicit
coverage failures. A zero or negative close cannot produce a priced holding or enter portfolio totals.
This task does not switch the running API from fixtures to live data.

## Read (only these)
- `docs/architecture.md`: Data providers, Canonical schemas and invariants, failure controls
- `docs/project-rules.md`
- `docs/decisions/ADR-002-scope-and-schedule.md`, `ADR-003-cost-and-data-rights.md`, `ADR-004-contracts-v1-1.md`
- `docs/tasks/T-000-phase0-decisions.md` (access), `docs/tasks/T-006-portfolio-valuation.md`
- `packages/contracts/schemas/{observation,evidence,valuation,common}.schema.json` (read-only)
- `apps/api/app/models/valuation.py`, `apps/api/app/domain/valuation.py`
- `apps/api/app/services/{instruments,portfolios}.py` (read-only)
- `apps/api/tests/{test_valuation,test_valuation_api,test_contracts_v1_1}.py`
- `apps/api/pyproject.toml`, `.env.example` (read-only; use existing dependencies)
- Official Alpaca historical bars/calendar and SEC submissions/access documentation: verify endpoint,
  pagination, timestamp, feed entitlement and rate-limit semantics before implementing; record links in handoff.

## Owned paths (edit only these)
- `apps/api/app/providers/` (transport, typed results, Alpaca and SEC adapters)
- `apps/api/app/domain/valuation.py`
- `apps/api/tests/test_providers.py` (new), `apps/api/tests/test_valuation.py`, `apps/api/tests/test_valuation_api.py`, `apps/api/tests/test_contracts_v1_1.py`
- `evals/fixtures/providers/` (new, wholly synthetic payloads)
- `docs/tasks/T-008-provider-adapters.md`, `docs/tasks/LEDGER.md`, `docs/handoffs/CURRENT.md`

## Inputs / outputs
- Inject transport, UTC clock, sleeper and stable instrument/symbol resolution; tests use fakes. No
  network or credential loading at import time. Configuration is supplied server-side; missing keys,
  feed or SEC contact string fail explicitly. Never read or print the private credentials file in tests.
- Alpaca input: explicit instrument UUID + effective-dated symbol, bounded session range, explicit feed
  (`sip` for the verified pilot), `adjustment=none`. Request daily bars only. Resolve regular/half-day
  session close via exchange calendar data, not the daily bar's bucket timestamp or a fixed UTC hour.
  Output validated `Observation` records for close (USD) and volume (shares), plus per-instrument errors
  and requested/covered sessions. Preserve feed; never silently substitute IEX or an adjusted series.
- Parse JSON numbers directly as Decimal; serialize decimal strings without a float round trip. Require
  positive finite closes; volume may be zero but must be finite and nonnegative. Missing fields are not
  zero. An invalid close rejects that bar and records a validation error.
- `observed_at` is the completed market session close; `received_at` is actual retrieval time from the
  injected clock. Historical retrieval must not backdate receipt. Stable IDs include instrument,
  metric, feed, session, adjustment, market time and normalized value; corrected values get new IDs.
- SEC input: explicit instrument UUID-to-CIK mapping, bounded filing date range and decision cutoff.
  Read submissions metadata (including historical pages needed for the range); preserve CIK,
  accession, form, filing date, acceptance time and primary-document name in a typed adapter record.
  Map to canonical Evidence with filing source type, accession-based source identity, SEC URL,
  UTC acceptance time as `published_at`, actual retrieval time as `known_at`, and a SHA-256 of the
  normalized source record whose exact hash input is documented. Use an explicit public-domain license
  tag. Do not fabricate a midnight publication time from a filing date; missing acceptance time is a
  validation error. No filing body download or excerpts in this task.
- Results expose records, coverage and typed errors (`configuration`, `authentication`, `rate_limited`,
  `timeout`, `upstream`, `invalid_payload`, `unresolved_identity`). Vendor fields stay inside adapters.
  Paginated results are incomplete until every required page succeeds; expose partial records explicitly.

## Non-positive close fix (required)
- Keep signed Observation inputs and strict positive valuation JSON Schema unchanged. The domain guard
  must work for legacy observations that bypass the adapter.
- Preserve existing currency, cutoff, session and adjustment eligibility checks. Select the latest
  eligible timestamp first. If any close at that timestamp is non-positive, return `price: null` and
  `market_value: {kind: unavailable, reason: no_price}`. Do not fall back to an older positive close or
  silently discard the invalid candidate to select another price at the same timestamp. Otherwise keep
  existing conflicting-price and unit-mismatch behavior.
- Exclude these holdings from priced totals and weight denominators; P/L and weight are unavailable
  with `market_value_unavailable`, coverage counts them under `no_price`, and total value remains
  unavailable when any position is unpriced. Valid negative P/L and zero supplied cash still work.
- Remove `test_non_positive_close_conforms` and its strict xfail decorator from
  `apps/api/tests/test_contracts_v1_1.py`; remove the unused `ValidationError` import. Replace it with
  ordinary passing, parametrized producer regression tests that assert unavailable behavior for zero
  and negative closes and validate the whole HTTP 200 response against the unchanged v1.1 schema.
  Do not merely delete coverage or remove the xfail while retaining a schema-only assertion.

## Failure and cutoff rules
- Per-request timeout 10 seconds; at most 3 attempts and 100 pages per call. Inject bounded backoff
  and jitter; honor Retry-After within a 60-second total call budget, otherwise return rate_limited.
  Retry transport timeouts, 429 and 5xx only; no retry for auth or invalid payloads. Detect repeated
  page tokens; enforce an SEC request limiter at no more than 5 requests/second per process. No fan-out
  in this task; deployment-wide coordination is required before multiple ingestion workers are enabled.
- Retrieved records after a decision cutoff cannot enter an as-of packet. Expose them as excluded
  coverage, not as evidence known at the cutoff. The valuation domain independently enforces both clocks.
- Missing sessions, partial pages and rejected records are visible coverage gaps. Old positive data may
  be returned with its true timestamps; freshness classification belongs to policy. Empty successful
  SEC results mean no filings in the requested range, not no material change. An outage means failed or
  partial coverage and cannot erase previously ingested records.
- Redact credentials and sensitive URLs in errors/logs. Source text and payloads are untrusted data.

## Acceptance fixtures
All payloads are synthetic; fake HTTP, time, sleep and calendars. No live APIs in tests.
- Ten instrument identities, including effective-dated ticker change and unresolved symbol/CIK.
- Full day, half-day, DST boundary, weekend/holiday and missing session; session close differs from
  daily bucket timestamp. Split fixture proves unadjusted closes and feed labels survive normalization.
- Decimal precision, zero/negative close (including negative zero), missing/null/non-finite value,
  zero volume, malformed timestamps, unknown feed and adjusted-price rejection.
- Pagination success, duplicate page replay, repeated token, page cap and later-page failure; retries
  obey limits, Retry-After and call budget. Auth and configuration failures never retry.
- SEC accession/document URL, acceptance time vs filing date, historical page, empty range, malformed
  parallel arrays, correction with distinct accession, and known_at after cutoff. Hash and IDs are
  deterministic for replayed records; changed content produces distinct identities.
- Domain and HTTP regressions for zero and negative close, latest invalid plus older valid, and
  simultaneous invalid/valid latest candidates; coverage, totals, unavailable P/L and weight agree.
- Positive closes, negative P/L, supplied zero cash and existing conflicting-price behavior still pass.
- Canonical Observation and Evidence outputs validate with JSON Schema format checking enabled.

## Validation commands
```
cd apps/api && uv run pytest tests/test_providers.py tests/test_valuation.py tests/test_valuation_api.py tests/test_contracts_v1_1.py
make test
make lint
make contracts && git diff --exit-code packages/contracts
```
Run the first command in a subshell or return to repo root before make. Unset a dev DATABASE_URL;
use the existing dedicated test database configuration for the full suite. No T-008 close xfails remain.

## Excluded scope / assumptions
- FRED is a separate follow-up despite ADR-003's broader provider roadmap; this task covers the ledger's
  Alpaca + SEC boundary. No FMP, news, JEV, live orders, intraday, universe screening or liquidity cadence.
- No persistence/migrations, scheduler, worker wiring, live valuation repository switch, new routes,
  shared contract changes or T-012 store follow-ups. Propose any necessary ownership expansion in handoff.
- Access is verified by T-000; endpoint behavior must still be checked against official documentation.
  There is no silent paid upgrade or feed fallback. Live smoke checks are optional and outside tests;
  never commit live payloads, account data or credentials.

## Planned commits
1. `docs:` provider spec, ready ledger row and handoff (this session).
2. `fix:` non-positive close guard with domain/API/conformance regressions; targeted valuation tests pass.
3. `feat:` bounded transport and Alpaca normalization with deterministic tests.
4. `feat:` SEC normalization and coverage with deterministic tests.
5. `docs:` final handoff and ledger after full validation.

## Handoff checklist
- [ ] Targeted tests, make test, make lint and unchanged contracts pass
- [ ] No non-positive close xfails or original test_non_positive_close_conforms remain
- [ ] Provider docs checked; timestamp, identity and hash mappings recorded
- [ ] CURRENT.md and LEDGER updated; branch committed and pushed
