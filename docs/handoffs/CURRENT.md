# Handoff — T-004 CSV validation and import preview

- **Updated:** 2026-09-26 23:35 SGT by Codex
- **Branch / worktree:** task/T-004-csv-import @ ~/code/ms-wt/api
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Claude Code reviews T-004, starting with `apps/api/app/services/imports.py`,
`apps/api/app/routes/imports.py`, and `apps/api/tests/test_imports_api.py`.
Run the task's three validation commands; review the generated OpenAPI diff.

## Done this session
- Implemented deterministic CSV parsing with preserved raw cells, Decimal validation,
  duplicate warnings, missing-cost nulls, formula detection, and explicit row issues.
- Added typed preview models and a replaceable in-memory repository with copy isolation.
- Added synchronous multipart `POST /imports` (201) and `GET /imports/{id}` (404 if absent).
- Enforced UTF-8/BOM, size, row-count, content-type, and required-header checks;
  rejected files never reach storage. Added uniform problem bodies for upload errors.
- Pinned python-multipart 0.0.20 and regenerated OpenAPI.
- Followed all six planned commits: parser tests (`60bc8ce`), parser (`a87408d`),
  models/repository (`0f169a9`), routes/OpenAPI (`549a410`), API tests (`aa8f304`),
  and this documentation commit. Branch is being pushed for review at session end.

## Tests run
- Initial parser tests failed as intended before implementation (missing service).
- Targeted API suite → pass: 50 tests, including 48 new import tests.
- `make test` → pass: 182 Python tests + 1 Vitest test; existing Starlette deprecation warning.
- `make lint` → pass: Ruff check/format, ESLint, Next type generation, TypeScript.
- `make contracts && git diff --exit-code packages/contracts` → pass; generated contract is current.

## Contract changes proposed (not applied)
- none; authorized OpenAPI regeneration is committed.

## Unresolved / assumptions
- Size limit interprets 1 MB as 1 MiB (1,048,576 bytes), documented in the endpoint.
- Accepted file MIME types: text/csv and application/csv; outer request must be multipart/form-data.
- Raw cells are ordered arrays aligned with detected columns, preserving extra cells and unknown columns.
  Uneven/blank rows remain visible with column_count_mismatch; duplicate recognized headers reject the file.
- Duplicate comparisons use parsed Decimal equality for valid holdings; no merge or symbol resolution.
- Preview storage is temporary and process-local (lost on restart, not shared across workers).
  No auth, tenant field, confirmation, or persistence was added, per scope.
