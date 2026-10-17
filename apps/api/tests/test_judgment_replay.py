"""Replay the recorded jev-1.13.0 responses over the adversarial packets, offline.

Raw JEV (no gates) is compared with expected.json here. Packets whose expectation is owned by a
deterministic gate (T-014) are asserted on the envelope in test_policy_envelope.py instead: JEV said
partial for 02's split and unusable for the evidence-only 03 and 10. Comparing the model to the
provisional labels is T-010's job; nothing is tuned away.

Stage-3 recordings predate exposure grounding (T-014), so their request bodies no longer match. Until
they are re-recorded, a stage-3 miss replays as unavailable and only stages 1-2 are snapshotted;
stage 3 is covered by the scripted transport in test_judgment_stages.py.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.judgment.client import JevClient, ReplayMiss, ReplayTransport
from app.judgment.stages import run_staged

ROOT = Path(__file__).resolve().parents[3]
PACKETS = ROOT / "evals/fixtures/packets"
RECORDINGS = ROOT / "evals/recordings/jev"
SCHEMAS = [json.loads(p.read_text()) for p in (ROOT / "packages/contracts/schemas").glob("*.json")]
REGISTRY = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in SCHEMAS)
JUDGMENTS = Draft202012Validator(
    {"$ref": "https://market-sentinel.local/schemas/decision.schema.json#/properties/judgments"},
    registry=REGISTRY,
)

# Recorded 2026-10-02 (stages 1-2). A change here means the mapping code or the recordings changed.
STAGE_2 = ("event_family", "primary_context", "novelty", "evidence_sufficiency")
SNAPSHOT = {
    "01-earnings-no-expectations": ("partial", "earnings", "unknown", "unclear", "insufficient"),
    "02-split-normalization": ("partial", "corporate_action", "company", "unclear", "partial"),
    "03-syndicated-single-source": ("unusable",),
    "04-catalyst-uncertain-response": ("partial", "regulatory", "unknown", "unclear", "partial"),
    "05-stale-feed": ("partial", "other", "unknown", "unclear", "partial"),
    "06-contradictory-sources": ("partial", "guidance", "unknown", "new", "partial"),
    "07-injection-in-evidence": ("unusable",),
    "08-lookahead": ("partial", "earnings", "unknown", "unclear", "partial"),
    "09-correction": ("partial", "earnings", "unknown", "update", "insufficient"),
    "10-failed-coverage": ("unusable",),
}
KEYS = ("data_usability", *STAGE_2)
STALE_STAGE_3 = {"classification_unavailable", "exposure_unavailable", "no_recorded_thesis"}

GATE_OWNED = {"02-split-normalization", "03-syndicated-single-source", "10-failed-coverage"}
MODEL_OWNED = sorted(set(SNAPSHOT) - GATE_OWNED)


class StagesOneAndTwo(ReplayTransport):
    def send(self, body):
        try:
            return super().send(body)
        except ReplayMiss:
            if "interpretation_conflict" not in json.loads(body)["questions"]:
                raise
            return 503, {}  # stale stage-3 recording: see the module docstring


def replay(name):
    client = JevClient(StagesOneAndTwo(RECORDINGS / name), max_attempts=1)
    return run_staged(PACKETS / name, client)


def expected(name):
    return json.loads((PACKETS / name / "expected.json").read_text())


@pytest.mark.parametrize("name", sorted(SNAPSHOT))
def test_replay_is_offline_schema_valid_and_matches_snapshot(name):
    result = replay(name)
    JUDGMENTS.validate(result.judgments)
    assert result.judgments == dict(zip(KEYS, SNAPSHOT[name], strict=False))
    assert result.model == "jev-1.13.0"
    assert result.excluded_evidence_ids == expected(name)["excluded_evidence_ids"]


@pytest.mark.parametrize("name", MODEL_OWNED)
def test_abstention_matches_expected(name):
    reasons = [r for r in replay(name).abstention_reasons if r not in STALE_STAGE_3]
    assert reasons == expected(name)["abstention_reasons"]


@pytest.mark.parametrize("name", [n for n in MODEL_OWNED if "data_usability" in expected(n)])
def test_data_usability_matches_expected(name):
    assert replay(name).judgments["data_usability"] == expected(name)["data_usability"]


def test_every_recording_is_pinned_and_successful():
    records = [json.loads(p.read_text()) for p in RECORDINGS.rglob("*.json")]
    assert len(records) == 24
    for record in records:
        assert record["status"] == 200
        assert record["request"]["model"] == record["response"]["model"] == "jev-1.13.0"
