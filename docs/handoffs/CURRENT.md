# Handoff — T-013 review: changes requested

- **Updated:** 2026-10-02 by Codex
- **Branch / worktree:** task/T-013-contracts-v1-1 @ ~/code/ms-wt/api
- **Status:** changes_requested

## Next step (exact — the next agent starts here)
Claude Code: address the two findings below with regression cases first. No implementation fixes were made during review. Reviewed origin/task/T-013-contracts-v1-1 at 3aaf300 after git fetch.

## Done this session
- Reviewed task spec, ADR-004, branch handoff, schemas, examples, producer tests and valuation/instrument producers.
- P2: new patterns accept trailing newlines. symbol_mapping.schema.json:13 accepts "EXCO\n", although FileInstrumentRepository rejects it as untrimmed. common.schema.json:35,40 accept "1.00\n" and "0.500000\n". Python jsonschema uses search and $ matches before a final newline. Add strict end-of-string enforcement that also works in the web validator, with regressions for these cases.
- P2: valuation.schema.json:78 requires positive price.value, but existing API producer accepts zero/negative closes. Reproduced by replacing fixture close values with "0" and "-1": GET valuation returns 200, then shared schema validation fails at positions[*].price. Existing producer tests use only positive closes and miss this gap. Resolve the producer/schema mismatch (coordinate ownership if producer validation changes); retain a conformance regression. The prior handoff acknowledged the gap, but future adapter validation does not protect the current producer.
- Additive inspection: existing common definitions are unchanged; new brief conditions act only on new optional fields. All 13 original v1 valid examples remain byte-equivalent as parsed documents and pass v1.1 validation.

## Tests run
- `python3 packages/contracts/tests/gen_examples.py` → 23 valid / 69 invalid; examples diff clean.
- `make test` → 375 pytest passed, 64 Vitest passed.
- `make lint` → passed.
- `make contracts && git diff --exit-code packages/contracts` → passed, no diff.
- Read-only edge reproductions → trailing-newline inputs accepted; zero/negative closes return 200 bodies rejected by valuation schema.
- Existing Starlette/AnyIO deprecation warning only.

## Contract changes proposed (not applied)
- None during review. ADR-004 remains proposed; T-013 needs re-review after findings are resolved.

## Unresolved / assumptions
- Optional pending_sources and issues are additive as implemented. Count/sum checks, mapping intervals/FKs, and issue decision membership remain application-level per ADR.
- T-012 fixes were pushed on task/T-012-postgres-store (b93fd5c); ready for Claude Code re-review. Its validation and follow-ups are in that branch's handoff.
- Carry forward: /briefs projection formatter, codegen, upload size limit, provider non-positive close validation, per-tenant keys and observation persistence.
