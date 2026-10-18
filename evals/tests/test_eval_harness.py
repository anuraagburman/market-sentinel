"""Offline T-010 acceptance checks; no provider clients are constructed."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from evals.harness.evaluate import (  # noqa: E402
    load_labels,
    policy_bypasses,
    render_report,
    run_arm,
    score,
)
from evals.harness.persona import PersonaTransport  # noqa: E402


class FakeMessages:
    def create(self, **request):
        schema = request["output_config"]["format"]["schema"]
        values = {key: prop["enum"][0] for key, prop in schema["properties"].items()}
        return {
            "content": [{"type": "text", "text": json.dumps(values)}],
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }


def test_persona_fake_transport_runs_through_decide():
    arm = run_arm("persona", lambda _: PersonaTransport(FakeMessages()))
    assert len(arm) == 10
    assert not policy_bypasses({"persona": arm})


def test_scoring_agreement_confusion_distance_and_abstentions():
    labels = {
        "a": {"labels": {"x": {"value": 4}}},
        "b": {"labels": {"x": {"value": 2}}},
        "c": {"labels": {"x": {"abstain": "unknown"}}},
    }
    answers = {
        "a": {"judgments": {"x": 3}},
        "b": {"judgments": {}},
        "c": {"judgments": {}},
    }
    result = score(labels, answers, "x")
    assert (result["n"], result["exact"], result["within_one"]) == (2, 0, 1)
    assert (result["abstentions"], result["covered"], result["over"]) == (1, 1, 1)
    assert result["confusion"][("2", "abstain")] == 1
    assert result["confusion"][("abstain", "abstain")] == 1


def test_rules_only_abstains_on_all_later_decisions():
    for answer in run_arm("rules-only").values():
        assert set(answer["judgments"]) == {"data_usability"}


def test_bypass_detects_injection_failure():
    arm = run_arm("rules-only")
    name = next(name for name in arm if name.startswith("07-"))
    arm[name]["research_action"] = "investigate_now"
    assert policy_bypasses({"fake": arm})


def test_report_is_deterministic_and_denominators_come_from_labels():
    labels = load_labels()
    arms = {"rules-only": run_arm("rules-only"), "JEV": run_arm("JEV")}
    report = render_report(labels, arms)
    assert report == render_report(labels, arms)
    for decision in next(iter(labels.values()))["labels"]:
        n = sum("value" in label["labels"][decision] for label in labels.values())
        assert score(labels, arms["JEV"], decision)["n"] == n
        assert f"{decision}: provisional" in report


def test_missing_persona_recordings_are_hard_error():
    with pytest.raises((FileNotFoundError, LookupError), match="persona|stage"):
        run_arm("persona", recording_root=ROOT / "evals/nonexistent-persona")


@pytest.mark.parametrize(
    "content",
    [[], [{"type": "text", "text": "not json"}], [{"type": "text", "text": "{}"}]],
)
def test_malformed_persona_is_recorded_and_degrades_to_gate_only(content):
    class Malformed:
        def create(self, **kwargs):
            return {
                "content": content,
                "usage": {"input_tokens": 10, "output_tokens": 1},
            }

    arm = run_arm("persona", lambda _: PersonaTransport(Malformed()))
    for name, answer in arm.items():
        assert set(answer["judgments"]) == {"data_usability"}
        if not name.startswith(("02-", "07-")):
            assert answer["versions"]["model"] == "unavailable"


def test_persona_records_once_replays_and_rejects_changed_hash(tmp_path):
    from app.judgment.client import ReplayMiss, encode_request
    from app.judgment.questions import render_stage
    from scripts.record_persona import StageFiles

    class Counting(PersonaTransport):
        calls = 0

        def send(self, body):
            self.calls += 1
            return super().send(body)

    inner = Counting(FakeMessages())
    body = encode_request({"packet": {}}, render_stage(1))
    first = StageFiles(inner, "fake", tmp_path).send(body)
    assert StageFiles(inner, "fake", tmp_path).send(body) == first
    assert inner.calls == 1
    record = json.loads((tmp_path / "fake/stage-1.json").read_text())
    assert "persona_raw" in record["response"]
    assert "labels" not in record["persona_request"]
    with pytest.raises(ReplayMiss, match="fake/stage-1"):
        StageFiles(inner, "fake", tmp_path).send(encode_request({}, render_stage(1)))


def test_persona_prompt_change_is_a_replay_miss(tmp_path, monkeypatch):
    from app.judgment.client import ReplayMiss, encode_request
    from app.judgment.questions import render_stage
    from evals.harness.evaluate import StrictReplay
    from scripts import record_persona

    body = encode_request({}, render_stage(1))
    record_persona.StageFiles(PersonaTransport(FakeMessages()), "fake", tmp_path).send(
        body
    )
    monkeypatch.setattr("evals.harness.persona.SYSTEM", "A changed persona prompt")
    with pytest.raises(ReplayMiss, match="stage-1"):
        StrictReplay(tmp_path / "fake").send(body)
    with pytest.raises(ReplayMiss, match="stage-1"):
        record_persona.StageFiles(
            PersonaTransport(FakeMessages()), "fake", tmp_path
        ).send(body)
