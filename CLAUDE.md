@AGENTS.md

## Claude Code specifics
- Default lane: `apps/web`, UX states, explanation/evidence presentation, taxonomy and rubric drafting.
  Reviewer lane: API, ingestion, analytics, eval harness (Codex implements those).
- Run `/clear` between tasks. The handoff file is the memory; the chat is disposable.
- Use subagents only for a genuinely broad search, never to "double-check" small edits.
- Reviews: read `git diff main...HEAD` and the task file, not whole directories.
