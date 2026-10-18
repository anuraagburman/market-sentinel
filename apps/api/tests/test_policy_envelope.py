import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from test_policy_exposure import valuation

from app.judgment.client import JevClient, ReplayTransport
from app.policy.envelope import decide

ROOT = Path(__file__).resolve().parents[3]
PACKETS = ROOT / "evals/fixtures/packets"
NAMES = sorted(p.name for p in PACKETS.iterdir() if p.is_dir())
SESSION_CLOSE = "2026-09-25T20:00:00Z"
VALUATION = valuation()


class Recorded(ReplayTransport):
    """Recorded jev-1.13.0 answers. A request that was never recorded raises ReplayMiss."""

    def __init__(self, name):
        super().__init__(ROOT / "evals/recordings/jev" / name)
        self.calls = 0

    def send(self, body):
        self.calls += 1
        return super().send(body)


class Down:
    def send(self, body):
        return 503, {}


class FailsAt(Recorded):
    """Replays recorded stages, then fails from stage `call` on with `status`."""

    def __init__(self, name, call, status):
        super().__init__(name)
        self.call, self.status = call, status

    def send(self, body):
        if self.calls + 1 >= self.call:
            self.calls += 1
            return self.status, {"error": {"message": "credit balance too low"}}
        return super().send(body)


def decide_with(name, transport=None, **kwargs):
    client = (
        None if transport is None else JevClient(transport, sleep=lambda _: None, max_attempts=1)
    )
    return decide(PACKETS / name, VALUATION, client, expected_session_close=SESSION_CLOSE, **kwargs)


# Recorded 2026-10-02 (stages 1-2) and 2026-10-18 (stage 3, and 03/10 stage 2). A change here means
# the policy, the gates or the recordings changed.
SNAPSHOT = {
    "01-earnings-no-expectations": ("insufficient_evidence", "partial", "insufficient", 4),
    "02-split-normalization": ("insufficient_evidence", "unusable", None, None),
    "03-syndicated-single-source": ("watch_condition", "partial", "partial", None),
    "04-catalyst-uncertain-response": ("review_today", "partial", "partial", 4),
    "05-stale-feed": ("watch_condition", "partial", "partial", 4),
    "06-contradictory-sources": ("review_today", "partial", "partial", 3),
    "07-injection-in-evidence": ("insufficient_evidence", "unusable", None, None),
    "08-lookahead": ("review_today", "partial", "partial", 4),
    "09-correction": ("insufficient_evidence", "partial", "insufficient", 4),
    "10-failed-coverage": ("insufficient_evidence", "partial", "insufficient", 3),
}


@pytest.mark.parametrize("name", NAMES)
def test_recorded_pipeline_matches_snapshot(name):
    envelope = decide_with(name, Recorded(name))
    judgments = envelope["judgments"]
    assert (
        envelope["research_action"],
        judgments["data_usability"],
        judgments.get("evidence_sufficiency"),
        judgments.get("research_relevance"),
    ) == SNAPSHOT[name]
    assert "classification_unavailable" not in envelope["abstention_reasons"]
    if judgments["data_usability"] != "unusable":
        assert envelope["versions"]["model"] == "jev-1.13.0"


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


@pytest.mark.parametrize(
    ("call", "status", "reason"),
    [(2, 402, "budget_skipped"), (3, 503, "classification_unavailable")],
)
def test_later_stage_outage_degrades_to_gate_only_envelope(call, status, reason):
    envelope = decide_with(
        "04-catalyst-uncertain-response", FailsAt("04-catalyst-uncertain-response", call, status)
    )
    assert envelope["versions"]["model"] == "unavailable"
    assert envelope["judgments"] == {"data_usability": "usable"}
    assert envelope["research_action"] == "insufficient_evidence"
    assert reason in envelope["abstention_reasons"]


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
