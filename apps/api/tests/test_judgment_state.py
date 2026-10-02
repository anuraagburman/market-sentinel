import json
import shutil
from pathlib import Path

import pytest

from app.judgment.state import build_state

PACKETS = Path(__file__).resolve().parents[3] / "evals/fixtures/packets"
ALL = sorted(p for p in PACKETS.iterdir() if p.is_dir())


@pytest.mark.parametrize("packet_dir", ALL, ids=lambda p: p.name)
def test_excluded_evidence_matches_expected(packet_dir):
    expected = json.loads((packet_dir / "expected.json").read_text())
    built = build_state(packet_dir)
    assert built.excluded_evidence_ids == expected["excluded_evidence_ids"]
    sent = {item["id"] for item in built.state["packet"]["evidence"]}
    assert sent.isdisjoint(built.excluded_evidence_ids)


def test_lookahead_evidence_and_its_claims_never_reach_the_model():
    built = build_state(PACKETS / "08-lookahead")
    text = json.dumps(built.state)
    assert '"ev-2"' not in text
    for claim in built.state["packet"]["claims"]:
        assert "ev-2" not in claim["evidence_ids"]


def test_superseded_original_is_dropped_but_correction_is_kept():
    built = build_state(PACKETS / "09-correction")
    ids = [item["id"] for item in built.state["packet"]["evidence"]]
    assert ids == ["ev-2"]
    assert built.state["packet"]["evidence"][0]["correction_of"] == "ev-1"


def test_state_carries_cutoff_and_gaps_and_omits_storage_fields():
    built = build_state(PACKETS / "01-earnings-no-expectations")
    packet = built.state["packet"]
    assert packet["cutoff"] == "2026-09-25T21:00:00Z"
    assert packet["coverage_gaps"] == ["Comparable expectations unavailable"]
    for item in packet["evidence"]:
        assert not {"url", "hash", "license_tag", "source_id"} & item.keys()


def test_missing_packet_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_state(tmp_path)


def test_observation_received_after_cutoff_is_excluded(tmp_path):
    packet = tmp_path / "packet"
    shutil.copytree(PACKETS / "01-earnings-no-expectations", packet)
    observations = json.loads((packet / "observations.json").read_text())
    late = {**observations[0], "id": "late-obs", "received_at": "2026-09-25T21:00:01Z"}
    (packet / "observations.json").write_text(json.dumps([*observations, late]))
    built = build_state(packet)
    assert built.excluded_observation_ids == ["late-obs"]
    assert [o["id"] for o in built.state["packet"]["observations"]] == [observations[0]["id"]]
