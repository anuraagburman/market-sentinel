# ADR-001 — Contracts v1: JSON Schema as the shared source of truth

- **Status:** proposed (awaiting Codex review on `task/T-002-schemas`)
- **Date:** 2026-09-26
- **Task:** T-002

## Context
The web (Claude Code) and API (Codex) lanes need one agreed shape for every entity before they split.
Blueprint §14 lists the entities and invariants; §7 the taxonomy.

## Decision
1. **JSON Schema draft 2020-12 in `packages/contracts/schemas/`** is canonical. Pydantic models and
   TypeScript types are *generated from or tested against* it (follow-up after T-001), never hand-forked.
2. **Money and quantities are decimal strings** (`"101.25"`), never JSON numbers, so no float rounding
   crosses a boundary.
3. **Timestamps must be UTC with a trailing `Z`, and a real date and time.** The pattern enforces shape and
   rejects offsets; `format: date-time` rejects impossible values such as `2026-02-30`. Format assertion is
   off by default in validators, so **every consumer must enable format checking** (Python `jsonschema`
   also needs `rfc3339-validator`; a test fails if it's missing).
4. **Unknown is explicit.** `Position.cost_basis` is a required key whose value may be `null`.
   Cash absent on a PortfolioVersion means unknown, not zero.
5. **Invariants live in the schema where expressible** (`if/then`), so fixtures fail loudly:
   unusable data or insufficient evidence ⇒ `insufficient_evidence`; abstention ⇒ ≥1 reason;
   revision > 1 ⇒ reason and predecessor; failed source ⇒ brief can't be `ready`/`no_material_change`;
   `no_material_change` ⇒ ≥1 checked source; plan prices come only from `user` or `calculation`.
6. **No confidence/probability field in v1.** Evidence *states* only. A calibrated value is added later by
   ADR, with its target and validation sample. A test bans the words from all schemas.
7. **Taxonomy ↔ envelope lock.** `decisions/taxonomy/v1.yaml` outputs must equal the envelope's judgment
   enums; `test_taxonomy_matches_decision_envelope` fails on drift.
8. **Horizon enum is `swing | multiweek`.** Intraday is excluded until feeds and latency are established.
9. `interpretation_conflict` uses `"yes" | "no"` strings (not booleans) so every choice decision shares one
   enum mechanism.

## Consequences
- Adding a taxonomy label is a two-file change (YAML + schema), plus version bump and eval re-run. Intended.
- Evidence and Claim ids are free strings (vendor/fixture ids like `ev-1`); entity ids are UUIDs.
- Cross-document rules (every observation in a decision satisfies its cutoff; claim ids resolve) can't be
  expressed in JSON Schema. They belong in the API's publish-time verifier (T-004+/T-009).

## Deferred
Codegen (Pydantic + TS) · DB tables and migrations · JEV vendor syntax · calibration fields ·
policy weights and thresholds (`TODO` in `decisions/policies/v1.yaml`, set after T-010 baselines).
