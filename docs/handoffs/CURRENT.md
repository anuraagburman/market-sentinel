# Handoff — T-013 contracts v1.1: review findings addressed

- **Updated:** 2026-10-02 by Claude Code
- **Branch / worktree:** task/T-013-contracts-v1-1 @ ~/code/ms-wt/web (detached push; the api worktree's local branch is behind, run `git pull --ff-only` there)
- **Status:** ready_for_review

## Next step (exact — the next agent starts here)
Codex: re-review `git diff 09a8046..origin/task/T-013-contracts-v1-1` (3 commits) against your two findings.
If they're resolved, merge T-013 to main with `--no-ff` and push main.

## Done this session
- P2 trailing newlines: the four v1.1 patterns (`money_string`, `weight_string`, `date`,
  `symbol_mapping.symbol`) now end in `$(?!\n)`. That rejects a final newline under Python `re.search` and
  ECMA-262 (Ajv). The v1 patterns keep plain `$`, so this bump doesn't narrow any v1 rule. ADR-004 records why.
  New invalid examples: money, weight, symbol and date, each with a trailing newline. The date case already
  failed through `format: date`; the pattern now rejects it without format checking.
- P2 non-positive close (user decision: keep the strict contract): `price.value` stays positive. A new
  `test_non_positive_close_conforms[0|-1]` is `xfail(strict=True, raises=ValidationError)`, so it fails as
  soon as the producer stops returning such prices. ADR-004 states the producer gap.

## Tests run
- `python3 packages/contracts/tests/gen_examples.py && git diff --exit-code …/examples` → 23 valid / 73 invalid, clean.
- Red step: 3 new invalid cases failed (money, weight, symbol) before the pattern fix.
- `make test` → 379 pytest passed, 2 xfailed (the tracked producer gap); 64 Vitest passed.
- `make lint` → exit 0. `make contracts && git diff --exit-code packages/contracts` → clean.

## Contract changes proposed (not applied)
- Optional v1.2: anchor the v1 patterns (`uuid`, `utc_timestamp`, `decimal_string`,
  `positive_decimal_string`, `currency`, `sha256`, feed version) the same way. Under ECMA-262 this narrows
  nothing; it only makes Python agree.

## Unresolved / assumptions
- Follow-up for Codex after T-012 merges: the valuation producer treats a non-positive close as unavailable
  (`no_price`, or a dedicated reason via a contract bump), and the strict xfail is removed. This is the T-008
  carry-forward "provider non-positive close rejection".
- T-012: Codex pushed fixes (`b93fd5c`); Claude Code re-review is pending.
- Carry forward: /briefs projection formatter, codegen, upload size limit, per-tenant keys, observation persistence.
