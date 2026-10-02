# ADR-005 — Retention and taxonomy label review

- **Status:** accepted (Anuraag, 2026-10-02)
- **Date:** 2026-10-02
- **Task:** T-000

## Context
T-000 left two decisions open: how long each kind of data is kept, and who reviews taxonomy labels.
The pilot has one user (ADR-003). The evidence policy calls labels **provisional** unless an experienced
practitioner labels them with written rubrics (`docs/evidence-policy.md`, eval set).

## Decision
1. **Retention**

   | Data | Rule |
   |---|---|
   | Holdings and portfolio versions | Kept until the user deletes them. Versions are immutable, so a delete removes the whole portfolio, never a single version. |
   | Evidence | Metadata, URL and hash kept indefinitely. Raw text from a vendor is kept only as long as that vendor's licence allows. Public-domain text (SEC, FRED) is kept indefinitely. |
   | Journals and paper decisions | Kept indefinitely. |
   | Raw model outputs | Kept 90 days. After that, only the typed judgment, its hash and the model id/version remain. |

2. **Label review:** Anuraag labels for now, and every label is marked **provisional**. No practitioner
   is engaged, so the cost is $0. Eval reports (T-010) carry the provisional status on every metric that
   depends on labels.

## Consequences
- The schema needs a delete path for holdings and portfolio versions that removes the whole portfolio,
  and a scheduled purge of raw model outputs once they are 90 days old. Neither is built yet; give each
  an owning task before multi-user delivery.
- Evidence rows need enough licence metadata (`license_tag`) to apply a vendor's retention limit.
- Recorded JEV fixtures under `evals/fixtures/` are test data, not user data. The 90-day purge does not
  apply to them.
- T-009 can start: taxonomy v1 ships with provisional labels.

## Open
- Name a qualified practitioner to review labels. Once one does, labels they review lose the
  provisional status.
- Decide what needs product or jurisdictional review before any public release (still open in T-000).
