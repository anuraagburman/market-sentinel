"""Provisional label files agree with taxonomy v1, policy gates, expected.json and packet hashes."""

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKETS = sorted((ROOT / "evals/fixtures/packets").iterdir())
LABELS = ROOT / "evals/labels/v1"
TAXONOMY = yaml.safe_load((ROOT / "decisions/taxonomy/v1.yaml").read_text())
POLICY = yaml.safe_load((ROOT / "decisions/policies/v1.yaml").read_text())
DECISIONS = {d["id"]: d for d in TAXONOMY["decisions"]}
LATER_STAGES = {
    d for s in TAXONOMY["staging"] if s["stage"] > 1 for d in s["decisions"]
}


def load(path):
    return json.loads(path.read_text())


def test_one_label_file_per_packet():
    assert sorted(p.stem for p in LABELS.glob("*.json")) == [p.name for p in PACKETS]


@pytest.mark.parametrize("folder", PACKETS, ids=lambda p: p.name)
def test_label_file(folder):
    doc = load(LABELS / f"{folder.name}.json")
    expected = load(folder / "expected.json")
    assert set(doc) <= {
        "packet",
        "packet_hash",
        "taxonomy_version",
        "status",
        "labeler",
        "labeled_at",
        "labels",
        "research_action",
    }
    assert doc["packet"] == folder.name
    # test_fixtures.py proves event.packet_hash is the hash of the frozen packet files.
    assert doc["packet_hash"] == load(folder / "event.json")["packet_hash"]
    assert doc["taxonomy_version"] == TAXONOMY["version"]
    assert doc["status"] == "provisional"
    assert doc["labeler"] == "anuraag"
    date.fromisoformat(doc["labeled_at"])

    labels = doc["labels"]
    assert set(labels) == set(DECISIONS)
    unusable = labels["data_usability"].get("value") == "unusable"
    for decision_id, label in labels.items():
        decision = DECISIONS[decision_id]
        assert set(label) in ({"value", "why"}, {"abstain", "why"}), decision_id
        assert label["why"].strip() and "\n" not in label["why"], decision_id
        if "value" in label:
            assert not (unusable and decision_id in LATER_STAGES), decision_id
            # Type check too: True == 1 and 4.0 == 4 would otherwise pass.
            assert any(
                label["value"] == o and type(label["value"]) is type(o)
                for o in decision["outputs"]
            ), decision_id
        else:
            allowed = set(decision["abstain_when"])
            if unusable and decision_id in LATER_STAGES:
                allowed = {"unusable_input"}
            assert label["abstain"] in allowed, decision_id

    if "data_usability" in expected:
        assert labels["data_usability"].get("value") == expected["data_usability"]

    # A label that trips a hard gate determines the research action, and only then is one given.
    values = {k: v["value"] for k, v in labels.items() if "value" in v}
    forced = {
        g["action"]
        for g in POLICY["hard_gates"]
        if "action" in g and all(values.get(k) == v for k, v in g["when"].items())
    }
    assert len(forced) <= 1
    action = doc.get("research_action")
    assert (action or {}).get("value") == next(iter(forced), None)
    if action:
        assert set(action) == {"value", "why"} and action["why"].strip()
        assert action["value"] == expected.get("research_action", action["value"])
    elif "research_action" in expected:
        pytest.fail("expected.json states a research_action the labels do not force")
