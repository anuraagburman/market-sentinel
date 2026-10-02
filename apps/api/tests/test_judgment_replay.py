"""Replay the recorded jev-1.13.0 responses over the adversarial packets, offline.

Disagreements with expected.json are tracked as strict xfails, not tuned away: comparing the model to
the provisional labels is T-010's job. A strict xfail starts failing once the behaviour changes.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.judgment.client import JevClient, ReplayTransport
from app.judgment.stages import run_staged

ROOT = Path(__file__).resolve().parents[3]
PACKETS = ROOT / "evals/fixtures/packets"
RECORDINGS = ROOT / "evals/fixtures/jev"
SCHEMAS = [json.loads(p.read_text()) for p in (ROOT / "packages/contracts/schemas").glob("*.json")]
REGISTRY = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in SCHEMAS)
JUDGMENTS = Draft202012Validator(
    {"$ref": "https://market-sentinel.local/schemas/decision.schema.json#/properties/judgments"},
    registry=REGISTRY,
)

# Recorded 2026-10-02. A change here means the mapping code or the recordings changed.
STAGE_2_3 = ("event_family", "primary_context", "novelty", "evidence_sufficiency")
SNAPSHOT = {
    "01-earnings-no-expectations": (
        "partial",
        "earnings",
        "unknown",
        "unclear",
        "insufficient",
        4,
        "no",
    ),
    "02-split-normalization": (
        "partial",
        "corporate_action",
        "company",
        "unclear",
        "partial",
        4,
        "no",
    ),
    "03-syndicated-single-source": ("unusable",),
    "04-catalyst-uncertain-response": (
        "partial",
        "regulatory",
        "unknown",
        "unclear",
        "partial",
        4,
        "no",
    ),
    "05-stale-feed": ("partial", "other", "unknown", "unclear", "partial", 4, "no"),
    "06-contradictory-sources": ("partial", "guidance", "unknown", "new", "partial", 3, "yes"),
    "07-injection-in-evidence": ("unusable",),
    "08-lookahead": ("partial", "earnings", "unknown", "unclear", "partial", 4, "no"),
    "09-correction": ("partial", "earnings", "unknown", "update", "insufficient", 4, "no"),
    "10-failed-coverage": ("unusable",),
}
KEYS = ("data_usability", *STAGE_2_3, "research_relevance", "interpretation_conflict")

DISAGREES = {
    "02-split-normalization": "JEV says partial (0.67); the split rule needs a deterministic gate",
    "03-syndicated-single-source": "JEV says unusable (0.74) for a packet with no observations",
    "10-failed-coverage": "JEV says unusable (0.59); expected a partial brief, not abstention",
}


def replay(name):
    client = JevClient(ReplayTransport(RECORDINGS / name), max_attempts=1)
    return run_staged(PACKETS / name, client)


def expected(name):
    return json.loads((PACKETS / name / "expected.json").read_text())


def tracked(names):
    return [
        pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=DISAGREES[n]))
        if n in DISAGREES
        else n
        for n in names
    ]


@pytest.mark.parametrize("name", sorted(SNAPSHOT))
def test_replay_is_offline_schema_valid_and_matches_snapshot(name):
    result = replay(name)
    JUDGMENTS.validate(result.judgments)
    assert result.judgments == dict(zip(KEYS, SNAPSHOT[name], strict=False))
    assert result.model == "jev-1.13.0"
    assert result.excluded_evidence_ids == expected(name)["excluded_evidence_ids"]


@pytest.mark.parametrize("name", tracked(sorted(SNAPSHOT)))
def test_abstention_matches_expected(name):
    reasons = [r for r in replay(name).abstention_reasons if r != "no_recorded_thesis"]
    assert reasons == expected(name)["abstention_reasons"]


@pytest.mark.parametrize(
    "name", tracked(sorted(n for n in SNAPSHOT if "data_usability" in expected(n)))
)
def test_data_usability_matches_expected(name):
    assert replay(name).judgments["data_usability"] == expected(name)["data_usability"]


def test_every_recording_is_pinned_and_successful():
    records = [json.loads(p.read_text()) for p in RECORDINGS.rglob("*.json")]
    assert len(records) == 24
    for record in records:
        assert record["status"] == 200
        assert record["request"]["model"] == record["response"]["model"] == "jev-1.13.0"
