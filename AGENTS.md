# Market Sentinel — agent instructions

Canonical instructions for **every** coding agent (Codex reads this file; Claude Code imports it via
`CLAUDE.md`). Keep it short. Detail lives in `docs/` — read only the doc your task points to.

## What this is
Evidence-first research product for active US-equity investors: morning brief, discovery,
volatile-day plans, thesis monitoring. Research and paper decisions only — **no live orders**.
Blueprint source: `docs/source/Market Sentinel Blueprint.pdf` (don't read it; use the split docs).

## Where to look (read on demand, not up front)
| Need | Read |
|---|---|
| Product scope, jobs, UX, acceptance | `docs/product.md` |
| JEV judgment, taxonomy, evidence, calibration | `docs/evidence-policy.md` |
| Stack, schemas, pipelines, API, failure handling | `docs/architecture.md` |
| Tests, release gates, phases | `docs/delivery.md` |
| How Claude Code + Codex share work | `docs/workflow.md` |
| Non-negotiable domain rules | `docs/project-rules.md` |

## Session start (every session, in this order)
1. Read `docs/handoffs/CURRENT.md` — it names the active task and the exact next step.
2. Read that task file in `docs/tasks/`. Touch **only its owned paths**.
3. Read only the docs/files the task lists. Do not scan the whole repo.

## Session end (every session, even when interrupted or near a usage limit)
1. Commit work-in-progress on the task branch (`wip:` prefix is fine). Never leave uncommitted work.
2. Overwrite `docs/handoffs/CURRENT.md` using `docs/handoffs/_TEMPLATE.md`.
3. Update the task's row in `docs/tasks/LEDGER.md`.

## Hard rules
- One active agent per worktree. Never edit a checkout another session is using.
- Shared contracts (`packages/contracts/`, `decisions/`, migrations) have one owner per task;
  propose changes in the handoff instead of editing them from someone else's task.
- Never use a generative model for portfolio arithmetic. Never turn missing data into zero.
- Tests are deterministic and never call live model or data APIs; use `evals/fixtures/`.
- No credentials, real holdings, or licensed raw text in Git.
- Report: behavior changed, tests run (with result), unresolved assumptions. "Done" means tests pass.

## Commands
Not defined yet — `T-001` creates them. Planned: `make dev`, `make test`, `make contracts`,
`make eval-smoke`, `make eval-heldout`, `make replay`.
