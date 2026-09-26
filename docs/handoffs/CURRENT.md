# Handoff — T-004 import review fixes

- **Updated:** 2026-09-26 23:42 SGT by Codex
- **Branch / worktree:** task/T-004-csv-import @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews the four import fixes (`b0be057`, `0826d54`, `1e4f00a`, `8b21178`),
starting with the parser and API regression tests. Re-run the task validation commands.

## Done this session
- Accepted Excel/plain-text/octet-stream MIME labels with case-insensitive .csv filenames;
  retained full content validation and regenerated OpenAPI.
- Formula cells now produce only formula_like_value for that field; other fields still validate.
- Blank CSV records remain visible with one blank_row warning and count toward the row limit.
- Negative cost basis is an import error (negative_cost_basis), preserved for review;
  explicit zero remains valid, and missing values remain null.
- Updated the task spec with the authorized scope additions and MIME/formula behavior.
- Each fix committed separately with passing targeted tests; ledger remains ready_for_review.

## Tests run
- Targeted API tests → pass: 34 tests.
- Targeted parser tests → pass: 39 tests.
- `make test` → pass: 210 Python tests + 1 Vitest test; existing Starlette deprecation warning.
- `make lint` → pass: Ruff check/format, ESLint, Next type generation, TypeScript.
- `make contracts && git diff --exit-code packages/contracts` → pass.

## Contract changes proposed (not applied)
- none; authorized OpenAPI description regeneration is committed.

## Unresolved / assumptions
- Blank means a CSV record with no cells; delimited empty cells still receive normal validation.
- Negative total cost requires review now, before T-006; it is never silently transformed.
- Existing scope: process-local temporary storage, no auth/confirmation/persistence;
  1 MiB file limit, 1,000 records, unresolved symbols remain pending for T-005.
