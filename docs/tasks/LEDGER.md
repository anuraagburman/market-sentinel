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
| T-006 | Deterministic portfolio valuation | 1 | Codex | Claude Code | task/T-006-valuation | T-005, ADR-002 | ready_to_merge |
| T-007 | Today page + evidence states (fixture-driven) | 1 | Claude Code | Codex | task/T-007-today | T-002, T-003 | merged |
| T-008 | Provider adapters (Alpaca, SEC EDGAR) | 1 | Codex | Claude Code | — | T-000, T-002 | backlog |
| T-009 | Staged JEV decisions (adapter + taxonomy v1) | 2 | Claude Code | Codex | — | T-000 (JEV access), T-003 | backlog |
| T-010 | First evaluation report (rules-only vs persona vs JEV) | 2 | Codex | Anuraag + Claude Code | — | T-009 | backlog |
| T-011 | Import confirm → immutable PortfolioVersion (persistence, duplicate removal) | 1 | Codex | Claude Code | — | T-005, T-006 | backlog |

**Parallel lanes right now:** Codex → T-006 review fix applied (`~/code/ms-wt/api`) · Claude Code → verify fix and merge T-006 · Anuraag → remaining T-000 (JEV access, Alpaca/SEC/FRED signups, retention, label reviewer).
