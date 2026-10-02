# Task ledger

Status: `backlog` (no spec yet) → `ready` (spec written) → `in_progress` → `review` → `ready_to_merge` → `merged` | `blocked`.
Write a full task file only when a task moves to `ready` — specs written too early go stale.

| ID | Task | Phase | Owner | Reviewer | Branch | Depends | Status |
|---|---|---|---|---|---|---|---|
| T-000 | Phase 0 decisions and access | 0 | Anuraag | Claude Code | main | — | ready |
| T-001 | Repo skeleton, Makefile, CI | 0 | Codex | Claude Code | task/T-001-skeleton | — | merged |
| T-002 | Core schemas and decision envelope | 0 | Claude Code | Codex | task/T-002-schemas | — | merged |
| T-003 | Synthetic fixtures (20-holding portfolio + 10 adversarial packets) | 0 | Codex | Claude Code | task/T-003-fixtures | T-001, T-002 | merged |
| T-004 | CSV validation and import preview | 1 | Codex | Claude Code | task/T-004-csv-import | T-001, T-002, T-003 | merged |
| T-005 | Instrument resolution | 1 | Codex | Claude Code | task/T-005-instrument-resolution | T-004 | merged |
| T-006 | Deterministic portfolio valuation | 1 | Codex | Claude Code | task/T-006-valuation | T-005, ADR-002 | merged |
| T-007 | Today page + evidence states (fixture-driven) | 1 | Claude Code | Codex | task/T-007-today | T-002, T-003 | merged |
| T-008 | Provider adapters (Alpaca, SEC EDGAR) | 1 | Codex | Claude Code | — | T-000, T-002 | backlog |
| T-009 | Staged JEV decisions (adapter + taxonomy v1) | 2 | Claude Code | Codex | task/T-009-jev-decisions | T-000 (JEV access), T-003 | ready |
| T-010 | First evaluation report (rules-only vs persona vs JEV) | 2 | Codex | Anuraag + Claude Code | — | T-009 | backlog |
| T-011 | Import confirm → immutable PortfolioVersion (row exclusion, idempotent confirm, in-memory store) | 1 | Codex | Claude Code | task/T-011-import-confirm | T-004, T-005, T-006 | merged |
| T-012 | Postgres portfolio + preview store (SQLAlchemy Core, first Alembic migration, per-import transactions, CI Postgres service) | 1 | Codex | Claude Code | task/T-012-postgres-store | T-011 | merged |
| T-013 | Contracts v1.1 bump (valuation, issue, instrument, symbol_mapping, brief.coverage.pending_sources) | 1 | Claude Code | Codex | task/T-013-contracts-v1-1 | T-005, T-006, T-007 | merged |

**Parallel lanes right now:** Codex → T-008 provider adapters next (T-012 and T-013 merged; T-008 also closes the non-positive close xfail from T-013) · Claude Code → free · Anuraag → remaining T-000 (pre-release review question, investor interviews; FMP and news optional). T-000 no longer blocks T-008 (keys verified 2026-10-02) or T-009 (ADR-005: provisional labels).
