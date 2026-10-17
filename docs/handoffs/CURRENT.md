# Handoff — T-009 Codex review: changes requested

- **Updated:** 2026-10-17 by Codex
- **Branch / worktree:** review/T-009-jev-decisions @ ~/code/ms-wt/api
- **Status:** changes_requested

## Next step (exact — the next agent starts here)
Claude Code: address the findings below on task/T-009-jev-decisions, starting with the
mixed-citation cutoff leak. The review commit can be cherry-picked from the review branch.
Review scope was `git diff origin/main...origin/task/T-009-jev-decisions` (tip 397efe7).
No implementation or recording was changed and no live API was called.

## Done this session
Reviewed the task brief, changed implementation/tests/recorder, taxonomy, evidence policy,
and packet 08/09 cutoff/correction behavior. Findings:

1. **[P1] Mixed citations retain excluded information in claim text —
   `apps/api/app/judgment/state.py:58-60`.** Filtering only the citation ids preserves the entire
   statement whenever any citation survives. A claim based partly on evidence first known after
   cutoff (or on a superseded original) therefore reaches JEV with its excluded content intact,
   now attributed only to the surviving source. Reproduced with packet 08: give claim-2 citations
   `[ev-1, ev-2]`; ev-2 is excluded, but “final revenue was 11.00 million USD” remains, linked to
   ev-1's preliminary 10.00 report. Drop claims with excluded dependencies unless their remaining
   support is independently validated; trimming ids is insufficient.
   **Regression test:** perturb packet 08 with those mixed citations and assert the final-revenue
   claim text never enters the state. Repeat with a superseded original in packet 09.

2. **[P2] Score validation checks keys but not probability values —
   `apps/api/app/judgment/stages.py:35-37`.** A five-key distribution containing strings is accepted
   and ranked lexicographically; mixing `None` with numbers raises `TypeError` and aborts the run.
   Negative, nonfinite and out-of-range values also pass. This violates the invalid-output path:
   malformed judgments should be omitted with `invalid_model_output`, not become ordinal levels
   or crash. Reproduced both string acceptance and the `None` crash offline.
   **Regression test:** parameterize stage-3 answers with strings, null, booleans, negative,
   nonfinite and out-of-range probabilities; assert relevance is omitted, the abstention is
   present, and other valid judgments survive. Preserve the existing numeric tie-down test.

3. **[P2] Malformed successful response containers bypass typed failure handling —
   `apps/api/app/judgment/client.py:181-185`.** HTTP 200 with `usage: null` raises `AttributeError`
   before the malformed-response guard. A top-level JSON list/null has the same problem. These
   are valid JSON, so LiveTransport's JSON error handling will not catch them; `_ask` only catches
   JevError, and the whole pipeline crashes instead of returning `classification_unavailable`.
   **Regression test:** fake 200 responses with top-level null/list and null/list usage; assert
   JevUnavailable from the client and classification_unavailable from run_staged, preserving
   completed stages. Validate the container types before calling `.get`.

4. **[P2] Recorder counts HTTP attempts as taxonomy stages —
   `scripts/record_jev.py:45-55`.** JevClient retries by invoking send again, so a stage-1
   429 followed by success creates stage-1.json and stage-2.json, both for data_usability.
   Subsequent actual stage-2/3 calls are labeled 3/4. This breaks the promised packet × stage
   recording format and corrupts metadata used to interpret recordings; the current tests cover
   retrying and recording separately and miss their composition. Replay's hash map also collapses
   duplicate requests, so it cannot reproduce the retry sequence.
   **Regression test:** run StageFiles with a fake 429 → 529 → success followed by stages 2/3,
   then assert semantic stage numbers stay 1/2/3 and the attempt history has an explicit,
   deterministic representation. No LiveTransport construction is needed.

## Tests run
- Targeted five `apps/api/tests/test_judgment_*.py` modules via `uv run --project apps/api pytest`
  → **77 passed, 4 xfailed**.
- `/tmp/t009_review_probe.py` with the existing API venv → reproduced all four findings using
  temporary packet copies and fake transports; no repository fixtures modified.
- Full suite/lint not rerun: review changes only handoff and ledger documentation.
- `git diff --check` → passed.

## Contract changes proposed (not applied)
- None. Retain implementer's optional future proposal to change interpretation_conflict to Noul
  only with a versioned policy threshold.

## Unresolved / assumptions
- Existing strict xfails are explicit model/fixture disagreements, not new review findings:
  packet 02 split gate; packets 03/10 evidence-only usability. Do not tune expectations to the model.
- Preserve implementer's follow-ups: deterministic split/freshness/identity policy and decision
  envelope, missing exposure for research_relevance, stage-1-unavailable envelope path, runtime
  PyYAML promotion, and a usable-packet injection probe. These remain outside this review's fixes.
- Provider billing status remains unverified; the client currently recognizes 402 and billing
  words on non-retryable errors. No live recording refresh was authorized or attempted.
- Review branch is isolated because task/T-009-jev-decisions is checked out in the web worktree.
  This session did not edit that worktree or merge either branch.
