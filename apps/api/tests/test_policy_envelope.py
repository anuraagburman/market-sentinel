import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from test_policy_exposure import valuation

from app.judgment.client import JevClient, ReplayMiss, ReplayTransport
from app.policy.envelope import decide

ROOT = Path(__file__).resolve().parents[3]
PACKETS = ROOT / "evals/fixtures/packets"
NAMES = sorted(p.name for p in PACKETS.iterdir() if p.is_dir())
SESSION_CLOSE = "2026-09-25T20:00:00Z"
VALUATION = valuation()


class Recorded(ReplayTransport):
    """Recorded jev-1.13.0 answers; anything not recorded (e.g. stale stage 3) is unavailable."""

    def __init__(self, name):
        super().__init__(ROOT / "evals/recordings/jev" / name)
        self.calls = 0

    def send(self, body):
        self.calls += 1
        try:
            return super().send(body)
        except ReplayMiss:
            return 503, {}


class Down:
    def send(self, body):
        return 503, {}


def decide_with(name, transport=None, **kwargs):
    client = (
        None if transport is None else JevClient(transport, sleep=lambda _: None, max_attempts=1)
    )
    return decide(PACKETS / name, VALUATION, client, expected_session_close=SESSION_CLOSE, **kwargs)


def expected(name):
    return json.loads((PACKETS / name / "expected.json").read_text())


@pytest.mark.parametrize("name", NAMES)
def test_recorded_envelope_matches_expected(name):
    envelope = decide_with(name, Recorded(name))
    want = expected(name)
    for key in ("data_usability",):
        if key in want:
            assert envelope["judgments"][key] == want[key]
    if "research_action" in want:
        assert envelope["research_action"] == want["research_action"]
    assert set(want["abstention_reasons"]) <= set(envelope["abstention_reasons"])
    assert set(envelope["evidence_ids"]).isdisjoint(want["excluded_evidence_ids"])


@pytest.mark.parametrize("name", ["02-split-normalization", "07-injection-in-evidence"])
def test_unusable_gate_skips_the_model(name):
    transport = Recorded(name)
    envelope = decide_with(name, transport)
    assert transport.calls == 0
    assert envelope["versions"]["model"] == "rules-only"
    assert envelope["judgments"] == {"data_usability": "unusable"}
    assert envelope["research_action"] == "insufficient_evidence"


@pytest.mark.parametrize("name", ["03-syndicated-single-source", "10-failed-coverage"])
def test_evidence_only_packets_are_partial_despite_recorded_unusable(name):
    envelope = decide_with(name, Recorded(name))
    assert envelope["judgments"]["data_usability"] == "partial"
    assert envelope["versions"]["model"] == "jev-1.13.0"
    assert "no_observations" in envelope["abstention_reasons"]
    assert "unusable_input" not in envelope["abstention_reasons"]


def test_stale_packet_cannot_investigate_now():
    envelope = decide_with("05-stale-feed", Recorded("05-stale-feed"))
    assert envelope["judgments"]["data_usability"] == "partial"
    assert envelope["research_action"] != "investigate_now"


def test_unpriced_holding_abstains_on_exposure():
    envelope = decide_with("03-syndicated-single-source")
    assert "exposure_unavailable" in envelope["abstention_reasons"]


@pytest.mark.parametrize("name", NAMES)
def test_rules_only_path_needs_no_model(name):
    envelope = decide_with(name)
    assert envelope["versions"] == {
        "taxonomy": "1.0",
        "policy": "1.1",
        "model": "rules-only",
        "calibration": None,
    }
    assert envelope["research_action"] == "insufficient_evidence"
    assert envelope["abstention_reasons"]


def test_provider_down_degrades_to_gate_only_envelope():
    envelope = decide_with("01-earnings-no-expectations", Down())
    assert envelope["versions"]["model"] == "unavailable"
    assert envelope["judgments"] == {"data_usability": "usable"}
    assert envelope["research_action"] == "insufficient_evidence"
    assert "classification_unavailable" in envelope["abstention_reasons"]


def test_envelope_carries_lineage_from_the_packet():
    envelope = decide_with("08-lookahead", Recorded("08-lookahead"))
    event = json.loads((PACKETS / "08-lookahead/event.json").read_text())
    assert envelope["event_id"] == event["id"]
    assert envelope["as_of"] == event["cutoff"]
    assert envelope["packet_hash"] == event["packet_hash"]
    assert envelope["evidence_ids"] == ["ev-1"]
    assert envelope["status"] == "published"
    assert envelope["raw_provider_output_ref"] is None


def test_reruns_are_byte_identical():
    first = decide_with("01-earnings-no-expectations", Recorded("01-earnings-no-expectations"))
    again = decide_with("01-earnings-no-expectations", Recorded("01-earnings-no-expectations"))
    assert json.dumps(first) == json.dumps(again)


def test_decision_id_depends_on_the_model():
    rules = decide_with("01-earnings-no-expectations")
    jev = decide_with("01-earnings-no-expectations", Recorded("01-earnings-no-expectations"))
    assert rules["decision_id"] != jev["decision_id"]


def test_schema_invalid_envelope_raises_instead_of_publishing():
    with pytest.raises(ValidationError):
        decide_with("01-earnings-no-expectations", horizon="intraday")
