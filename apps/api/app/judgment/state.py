"""Build JEV state from an evidence packet directory.

Deterministic exclusions run here, before anything reaches a model: evidence and observations first
known after the cutoff (lookahead), and originals superseded by a correction known at the cutoff.
Excluded ids are returned for the audit record. Nothing missing is filled in.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

EVIDENCE_FIELDS = (
    "id",
    "source_type",
    "originator",
    "canonical_story_id",
    "published_at",
    "known_at",
    "excerpt",
    "correction_of",
)


@dataclass(frozen=True)
class BuiltState:
    state: dict
    excluded_evidence_ids: list[str]
    excluded_observation_ids: list[str]


def _read(packet_dir: Path, name: str):
    return json.loads((packet_dir / name).read_text())


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_state(packet_dir: Path) -> BuiltState:
    event = _read(packet_dir, "event.json")
    evidence = _read(packet_dir, "evidence.json")
    claims = _read(packet_dir, "claims.json")
    observations = _read(packet_dir, "observations.json")
    cutoff = _at(event["cutoff"])

    known = [item for item in evidence if _at(item["known_at"]) <= cutoff]
    superseded = {item["correction_of"] for item in known if item.get("correction_of")}
    kept = [item for item in known if item["id"] not in superseded]
    kept_ids = {item["id"] for item in kept}
    excluded = [item["id"] for item in evidence if item["id"] not in kept_ids]

    sent_observations = [o for o in observations if _at(o["received_at"]) <= cutoff]
    late_observations = [o["id"] for o in observations if _at(o["received_at"]) > cutoff]

    sent_claims = []
    for claim in claims:
        cited = [ev for ev in claim["evidence_ids"] if ev in kept_ids]
        if cited:
            sent_claims.append({**claim, "evidence_ids": cited})

    packet = {
        "cutoff": event["cutoff"],
        "event": {
            "id": event["id"],
            "event_type": event["event_type"],
            "instrument_ids": event["instrument_ids"],
        },
        "observations": sent_observations,
        "claims": sent_claims,
        "evidence": [{k: item[k] for k in EVIDENCE_FIELDS if k in item} for item in kept],
        "coverage_gaps": event.get("coverage_gaps", []),
    }
    return BuiltState(
        state={"packet": packet},
        excluded_evidence_ids=excluded,
        excluded_observation_ids=late_observations,
    )
