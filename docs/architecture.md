# Architecture (blueprint §11–16)

## Stack
Modular monolith: one repo, web app, Python API, background workers, shared contracts. Modules:
ingestion, research, decisions, delivery. No microservices until evidence justifies them.

| Layer | Choice | Boundary |
|---|---|---|
| Web | Next.js, React, TypeScript | responsive, typed UI |
| UI | Tailwind + accessible primitives | own the design tokens |
| API | FastAPI + Pydantic | typed validation, OpenAPI contracts |
| Analytics | Python, pandas or Polars, NumPy | deterministic features and portfolio math |
| Storage | PostgreSQL + SQLAlchemy/Alembic | source of truth, tenant isolation |
| Jobs | Celery + Redis | retryable work; DB stores durable run state |
| Files | S3-compatible private storage | uploads, licensed evidence snapshots |
| Models | JEV adapter + one generative adapter | replaceable, versions recorded |
| Tests | pytest, Vitest, Playwright | logic, UI, end-to-end |
| Ops | Docker Compose, CI, structured logs | reproducible local setup |

Pin versions and lockfiles. No vector search until analogue retrieval proves a need.

## System flow
Providers → ingestion/normalization → point-in-time snapshot → quantitative candidate detection →
bounded JEV triage → research packet → JEV evidence judgments → deterministic policy → verified
explanation → brief / discovery result / plan update.

Separate outcome pipeline evaluates archived decisions after horizons mature; **never mutates the
as-of packet**. Frontend reads published, versioned artifacts, not several live queries.

Deploy: frontend, API, workers as separate processes from one codebase. Managed Postgres + private
object storage for pilot. Separate dev/staging/prod credentials. One scheduler per job family;
workers claim durable runs with leases. Staging before any real holdings.

## Repository structure
```
market-sentinel/
  AGENTS.md  CLAUDE.md  README.md  .env.example  compose.yaml  Makefile
  apps/web/{app,components,lib,tests}          # Today Portfolio Discover Plans; EvidencePanel, FreshnessBadge
  apps/api/app/{routes,domain,providers,services,models,db}  apps/api/{migrations,tests}
  workers/{jobs,scheduler}                     # ingest, brief, investigate, monitor; calendar-aware
  packages/{contracts,design-tokens}           # OpenAPI + JSON Schema; spacing/color/type/motion
  decisions/{taxonomy/v1.yaml,rubrics,policies/v1.yaml,calibration}
  prompts/{extraction,explanation,counterevidence}/v1.md
  evals/{fixtures,labels,suites,reports}       # reports: aggregates only, no private data
  docs/{product,architecture,evidence-policy,delivery,workflow}.md  docs/{decisions,tasks,handoffs}
  infra/  scripts/  .github/workflows/
```
Generated clients derive from the backend contract; CI flags stale generated files.

## Data providers
| Need | Candidate | Qualification |
|---|---|---|
| Prices/bars | Alpaca | IEX is one venue; SIP consolidated coverage/entitlement differ. Set and store the feed explicitly. [S2] |
| Filings | SEC EDGAR | submissions + XBRL; preserve accession and filing dates [S3] |
| Fundamentals/calendars | Financial Modeling Prep | verify endpoints, history, delay, plan [S4] |
| Macro | FRED (+ vintages) | revised values need as-of handling [S5] |
| Announcements | issuer IR pages | coverage varies; archive only as permitted |
| News | licensed vendor chosen in Phase 0 | original pub time, corrections, redistribution, model rights |

Sources are adapters; no business rule depends on vendor field names. Never mix single-venue volume
with consolidated baselines. Label delayed data on cards and charts. Provider test set: 10 instruments,
an earnings-date change, a split, a ticker change, a missing session, a correction.

License ledger per dataset: users, display, derived data, model processing, retention, caching,
attribution, termination. Personal subscription ≠ public redistribution. Cost model: instruments ×
polling, events × model calls, storage, notifications; record real token use, retries, cache hits,
per-brief cost in shadow mode.

## Canonical schemas and invariants
UUID ids; UTC tz-aware timestamps; decimal money/quantities; explicit currency; immutable published
versions; tickers are labels, instruments have stable ids + effective-dated symbol maps.

| Entity | Essential fields | Invariant |
|---|---|---|
| PortfolioVersion | id, tenant_id, base_currency, imported_at, source_hash | confirmed version immutable |
| Position | portfolio_version_id, instrument_id, quantity, cost_basis, currency | null cost basis stays unknown |
| Observation | instrument_id, value, unit, feed, observed_at, received_at | keep adjustment + session metadata |
| Evidence | source_id, url, published_at, known_at, hash, license_tag | access respects retention + tenancy |
| Claim | statement, evidence_ids, relation, extraction_version | support/contradiction explicit |
| Event | instrument_ids, event_type, cutoff, packet_hash | stable dedup identity |
| Decision | event_id, taxonomy_version, model_id, outputs, status | versioned with evidence + policy lineage |
| Brief | portfolio_version_id, cutoff, decision_ids, coverage, revision | never mutates silently |
| Plan | thesis_version, horizon, conditions, invalidation, paper_size | user edits create a revision |
| Run | stage, idempotency_key, attempts, state, error_code | retry never duplicates publication |

Decision envelope (application contract, not vendor syntax):
```json
{
  "schema_version": "1.0",
  "decision_id": "uuid",
  "event_id": "uuid",
  "as_of": "2026-09-25T12:00:00Z",
  "horizon": "swing",
  "packet_hash": "sha256:...",
  "evidence_ids": ["ev-1", "ev-2"],
  "versions": {"taxonomy": "1.0", "policy": "1.0", "model": "record-provider-model-id", "calibration": null},
  "judgments": {"evidence_sufficiency": "partial"},
  "raw_provider_output_ref": "private-object-reference",
  "research_action": "watch_condition",
  "abstention_reasons": ["missing_expectations_data"]
}
```
Validate all references before publishing; every observation in an as-of decision satisfies its
known-at cutoff; raw output retained privately, sensitive fields minimized.

## Pipelines
**Import & valuation:** upload to private quarantine; enforce size/encoding/row/content-type limits;
parse as data (never formulas); map columns, normalize units, resolve instruments, row-level errors;
confirm transactionally → PortfolioVersion + valuation job; keep file hash. Value with synchronized
price + FX cutoffs; cash only if supplied; incomplete valuation shown as such; split-adjusted history
≠ actual prices for paper fills.

**Morning brief:** scheduler resolves exchange calendar + prefs, freezes cutoff, creates durable run
→ ingest → features/candidates → bounded research → JEV → policy → explanation from approved claims
only → citation + numeric checks → atomic publish. Keep last good brief but never label it current
during an outage. Late corrections = new revision with reason. Outbox record coordinates publish +
notification.

**Discovery / volatile-day:** intent → visible filter contract → deterministic screen → bounded
candidate evaluation. Volatile-day joins scheduled events, market context, exposure; updates saved
conditions. Debounce intraday observations; refresh only affected packets.

## API surface (proposed)
| Endpoint | Purpose | Behavior |
|---|---|---|
| POST /imports | create upload + validation job | 202 + job id |
| GET /imports/{id} | preview mappings + errors | explicit unresolved rows |
| POST /imports/{id}/confirm | commit portfolio version | idempotency key required |
| GET /briefs/latest | latest published brief | cutoff, coverage, revision |
| POST /research/search | bounded discovery | filters + job id |
| GET /decisions/{id} | decision + evidence | versioned read model |
| POST /plans | save research plan | validated conditions |
| GET /jobs/{id} | background work | running, partial, failed, complete |

Tenant authorization everywhere; paginate evidence and journals; SSE or modest polling for progress;
never stream unverified model prose into a finished-looking brief.

## Runtime components ("agent" = bounded component with typed I/O, tools, stop condition)
| Component | Does | Must not |
|---|---|---|
| Catalyst researcher | primary event evidence + chronology | invent a cause from price |
| Market-context researcher | benchmarks, peers, regime | treat correlation as proof |
| Fundamentals researcher | normalize reported values + expectations | mix fiscal periods/currencies |
| Counterevidence researcher | seek evidence against hypothesis | manufacture symmetric arguments |
| JEV classifier | versioned bounded questions | exact portfolio arithmetic |
| Policy engine | integrity gates, priorities | let narrative override hard gates |
| Explanation writer | summarize approved facts | new claims or price targets |
| Verification | refs, numbers, schema, coverage | assume another model is ground truth |

Controls per research task: cutoff, source allowlist, request budget, max attempts, timeout, output
schema; cap depth and model calls per event; circuit breaker per provider; cache shared evidence
separately from private interpretation. Idempotency key = stage + event + cutoff + version; DB
uniqueness + transactional publish; bounded exponential backoff with jitter; permanent errors → visible
failed state.

Degraded: JEV down → deterministic observations labeled "classification unavailable" or partial
brief. Explanation down → template from validated fields. Key source missing → abstain on dependents.
Fallback model needs its own eval + version; never inherits JEV calibration.

Security: news, filings, uploads, retrieved text are **untrusted data** — can't authorize tools,
reveal secrets, or change policy. Server-side creds, least privilege, tenant isolation, encryption,
redacted logs, deletion workflows, secret scanning. Auth tests must attempt cross-tenant access.

## Operations
Track provider availability, ingestion lag, queue age, time to brief, model latency, validation
failure rate, abstention rate, coverage, dedup, notification delivery, cost per artifact; one trace id
end to end; logs carry ids/statuses, not portfolio values. Proposed SLOs: 95% of briefs ready ≤10 min
after cutoff; p95 cached page <2s — measured separately from freshness. Release manifest versions
provider mappings, prompts, taxonomy, calibration, policy together; shadow cohort before promotion;
rollback on integrity/eval regression; test backups by restoring. Budget: daily event and model-call
ceilings; stop optional enrichment when exhausted and show partial.
