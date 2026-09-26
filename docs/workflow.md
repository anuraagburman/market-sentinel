# Working with Claude Code + Codex

Two goals: **spend tokens only on work that moves a task**, and **never stall** when one tool
hits a usage limit, errors, or goes quiet. The mechanism for both is the same: state lives in
files and Git, never in a chat thread.

## 1. Lanes (blueprint §17)

One implementer per task, the other tool reviews. Rotate when it helps quality.

| Workstream | Implements | Reviews |
|---|---|---|
| UX flows, component states (`apps/web`) | Claude Code | Codex: contracts, edge cases |
| API, ingestion, deterministic analytics (`apps/api`, `workers`) | Codex | Claude Code: design, readability |
| Taxonomy and rubrics (`decisions/`) | Anuraag + Claude Code drafting | Codex: ambiguity, testability |
| Eval harness, leakage tests (`evals/`) | Codex | Anuraag + Claude Code |
| Explanations, evidence presentation (`prompts/`, web) | Claude Code | Codex: provenance, numeric fidelity |
| Integration, release | Anuraag + either | the other tool reviews the final diff |

**Contracts first.** `packages/contracts/` and `docs/architecture.md` §schemas are agreed before
the web and API lanes split. Then both lanes run in parallel against fixtures.

## 2. Worktrees: parallel without collisions

```
~/code/market-sentinel            main — integration only (Anuraag merges here)
~/code/ms-wt/web                  Claude Code window  (branch: task/T-xxx-...)
~/code/ms-wt/api                  Codex window        (branch: task/T-yyy-...)
```
Create one: `git worktree add ../ms-wt/api -b task/T-004-csv-validation`
Open each worktree in its own VS Code window. **One active agent per worktree, always.**

## 3. The relay: development doesn't stop

When the active tool hits a limit, errors repeatedly, or you're switching:

1. **Checkpoint** (in the tool that's stopping, if it can still respond):
   > Checkpoint now: commit WIP on this branch, overwrite docs/handoffs/CURRENT.md from the
   > template with the exact next step, update LEDGER.md. Stop after that.
2. If it can't respond: commit yourself (`git add -A && git commit -m "wip: T-xxx"`); the
   next agent reconstructs from `git diff main...HEAD` + the task file.
3. **Close that session**, then open the other tool **in the same worktree** and paste:
   > Resume. Read docs/handoffs/CURRENT.md and the task it names. Continue from "Next step".
4. When the first tool's limit resets, give it the **review** of what the second one did, or a
   different lane. Don't hand the same task back and forth mid-step.

Keep a parked task in each lane (LEDGER status `ready`) so the idle tool always has work.

## 4. Token discipline

**Context is the cost.** Every turn re-reads everything already in the conversation.

- **One task = one fresh session.** `/clear` in Claude Code, new thread in Codex. Long threads are
  the single biggest waste.
- **Small tasks.** A task should fit in one session: ≤ ~5 files touched, one behavior, its tests.
  If an agent needs to "understand the codebase" first, the task is too vague — rewrite it.
- **Point, don't browse.** Task files list the exact files and doc sections to read. `AGENTS.md`
  is an index, not an encyclopedia; keep it under ~60 lines.
- **Review diffs, not repos.** Reviewer reads `git diff main...HEAD` + the task file only.
- **Match effort to the work.**
  - High reasoning: taxonomy, schemas, evidence policy, leakage design, tricky bugs.
  - Default/low: CRUD routes, UI states from a spec, fixtures, renames, test scaffolds.
- **Tests over back-and-forth.** Ask the agent to run the targeted test and fix until green;
  don't paste outputs back and forth yourself.
- **Keep generated and bulky files out of reach.** `node_modules`, lockfiles, generated clients,
  fixtures >100 KB, and the PDF are never read unless the task says so.
- **No live APIs in the loop.** Fixtures make every run cheap and repeatable.
- **Don't let both tools do the same thing.** Review ≠ re-implement. Reviewer reports findings;
  implementer fixes.

## 5. Daily loop

1. Pick the next `ready` task in `docs/tasks/LEDGER.md`; if none, write one from `_TEMPLATE.md`
   (or ask Claude Code to draft it — cheap, and it's your spec).
2. Implementer works in its worktree; runs targeted tests; commits; writes handoff.
3. Reviewer (other tool, fresh session, same branch): *"Review this branch against
   docs/tasks/T-xxx.md. Read only `git diff main...HEAD`. Report concrete failures with file:line
   and a test that would catch each. Don't rewrite unrelated code."*
4. Implementer fixes findings. You run `make test`, read the diff, merge to `main`.
5. Record an ADR in `docs/decisions/` whenever a contract or design choice changes.

## 6. Prompt starters

**Codex — implement**
> Implement docs/tasks/T-xxx.md. Own only the paths it lists. Preserve the OpenAPI contract unless
> you first propose a change in the handoff. Run the task's validation commands until green.
> End with: behavior changed, tests run, unresolved assumptions; then update the handoff + ledger.

**Claude Code — implement**
> Implement docs/tasks/T-xxx.md. Own only the paths it lists. Include ready, partial, stale, failed,
> and no_material_change states. Never invent confidence percentages or fill missing data. Run the
> tests, then update the handoff + ledger.

**Either — adversarial review**
> Review this branch against docs/evidence-policy.md and the task. Look for future-data leakage,
> unsupported citations, model-performed arithmetic, stale-feed readiness, duplicate publication,
> tenant leakage. Report reproducible findings with severity. Don't broaden the implementation.

## 7. Case-study log

Blueprint §22 wants a record of how the tools split work and what the human caught. Add one line
per merged task to `docs/handoffs/case-study-log.md`: task, implementer, reviewer, what review
caught, what you caught.
