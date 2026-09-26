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

## Synthetic instrument master

`instruments/instruments.json` and `instruments/symbol_mappings.json` are generated
reference data for T-005, temporary until provider reference data (T-008). They are
entirely fictional and must not be used to identify real securities. Instrument
IDs for Synthela 01–19 match `portfolio/positions.json`; new instruments use the
reserved UUID suffixes 1001–1004, outside the existing generated ID range.

Mappings use inclusive `valid_from` and exclusive `valid_to` dates; null means
open-ended. The master covers common/preferred shares, ambiguous `SYN-AMB`, the
Synthela 20 ticker change on 2026-06-01, and `SYN-RE` reuse on 2026-07-01 from
CAD-denominated Synthela 21 to USD-denominated Synthela 22. `SYN-TYPO` has no mapping.
The prescribed ambiguity fixture includes simultaneous aliases for both Synthela
02 instruments. Local fixture schemas validate these records pending a shared
contract version bump; existing v1 contract schemas are unchanged.
