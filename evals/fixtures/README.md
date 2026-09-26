# Frozen synthetic fixtures — v1

Run `python3 evals/fixtures/generate.py` from the repository root to rebuild all
CSV/JSON data. The generator has no network calls, randomness or wall-clock input.
All evidence is synthetic, uses example.com URLs, and has license_tag synthetic.

Entity objects validate against contracts v1 with date-time checking. Plural files
are arrays whose individual elements validate against the singular entity schema.
`expected.json` is local test metadata, not a decision envelope or JEV label set;
its strict schema lives in evals/tests/test_fixtures.py. No contract changes are
needed. Missing judgment outputs and research actions are deliberately omitted.

## Packet hashes

Hash UTF-8 bytes of `json.dumps(packet, sort_keys=True, separators=(",", ":"))`
(default ensure_ascii=True), where packet is an object with exactly three keys:
`evidence.json`, `claims.json`, `observations.json`, each containing its parsed JSON
array. Array order is preserved. Prefix the SHA-256 hex digest with `sha256:`.
The hash covers the frozen raw packet, including excluded evidence and its claims.
Evidence hashes cover UTF-8 excerpt bytes; source_hash covers the exact CSV bytes.

## Integrity expectations

`excluded_evidence_ids` excludes items from downstream use, preserving audit data:
08 excludes post-cutoff knowledge; 09 excludes the superseded original. Consumers
must also exclude claims depending on those items. Packet 03 shares story and
originator across ten URLs. Packet 06 retains both supported sides of a conflict.
Packet 07 pairs malicious source text with missing required observations so the
unusable-input gate cannot be overridden. No real policy engine is implemented.

Packet 05's week-old close is explicitly stale for this fixture's morning-brief
use case; no production freshness threshold is invented. `disabled_effects` lists
hard-gate effects required by policy v1. Packet 10's brief is the expected partial
output; no decision is fabricated for the failed coverage.
