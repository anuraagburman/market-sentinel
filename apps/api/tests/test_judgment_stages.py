import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.judgment.client import JevClient
from app.judgment.stages import run_staged, score_level

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "evals/fixtures/packets/01-earnings-no-expectations"
SCHEMAS = [json.loads(p.read_text()) for p in (ROOT / "packages/contracts/schemas").glob("*.json")]
REGISTRY = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in SCHEMAS)
DECISION_ID = "https://market-sentinel.local/schemas/decision.schema.json"
JUDGMENTS = Draft202012Validator(
    {"$ref": f"{DECISION_ID}#/properties/judgments"}, registry=REGISTRY
)


def choice(value):
    return {"type": "choice", "choice": value, "probabilities": {value: 1.0}, "confidence": 1.0}


def score(probabilities):
    return {"type": "score", "score": 0.0, "probabilities": probabilities, "confidence": 0.5}


STAGE_2 = {
    "event_family": choice("earnings"),
    "primary_context": choice("company"),
    "novelty": choice("new"),
    "evidence_sufficiency": choice("partial"),
}
STAGE_3 = {
    "thesis_impact": choice("unclear"),
    "research_relevance": score({"0": 0.1, "1": 0.2, "2": 0.6, "3": 0.1, "4": 0.0}),
    "interpretation_conflict": choice("no"),
}


class ScriptedTransport:
    """Answers each call from the scripted answers for exactly the questions it was asked."""

    def __init__(self, answers, failures=None):
        self.answers = answers
        self.failures = failures or {}
        self.calls = []

    def send(self, body):
        request = json.loads(body)
        asked = sorted(request["questions"])
        self.calls.append((asked, request["state"]))
        for key, reply in self.failures.items():
            if key in asked:
                return reply
        answers = {q: self.answers[q] for q in asked if q in self.answers}
        return 200, {
            "model": "jev-1.13.0",
            "answers": answers,
            "usage": {"input_tokens": 1000},
        }


def run(answers, thesis="Margins expand through 2027", failures=None):
    transport = ScriptedTransport(answers, failures)
    client = JevClient(transport, sleep=lambda _: None, max_attempts=1)
    return run_staged(PACKET, client, thesis=thesis), transport


def test_full_run_produces_schema_valid_judgments_across_three_calls():
    result, transport = run({"data_usability": choice("usable"), **STAGE_2, **STAGE_3})
    JUDGMENTS.validate(result.judgments)
    assert [asked for asked, _ in transport.calls] == [
        ["data_usability"],
        sorted(STAGE_2),
        sorted(STAGE_3),
    ]
    assert result.judgments["research_relevance"] == 3
    assert result.abstention_reasons == []
    assert result.input_tokens == 3000
    assert result.cost == Decimal("0.000126")
    assert result.model == "jev-1.13.0"


def test_unusable_stops_after_stage_one():
    result, transport = run({"data_usability": choice("unusable")})
    assert len(transport.calls) == 1
    assert result.judgments == {"data_usability": "unusable"}
    assert result.abstention_reasons == ["unusable_input"]


def test_invalid_stage_two_answer_is_omitted_and_blocks_stage_three():
    result, transport = run(
        {"data_usability": choice("usable"), **STAGE_2, "novelty": choice("brand_new")}
    )
    assert len(transport.calls) == 2
    assert "novelty" not in result.judgments
    assert result.judgments["event_family"] == "earnings"
    assert result.abstention_reasons == ["invalid_model_output"]


def test_missing_answer_is_invalid_output():
    stage_2 = {k: v for k, v in STAGE_2.items() if k != "novelty"}
    result, _ = run({"data_usability": choice("usable"), **stage_2})
    assert "novelty" not in result.judgments
    assert "invalid_model_output" in result.abstention_reasons


def test_stage_three_sees_earlier_judgments_labelled_and_the_thesis():
    _, transport = run({"data_usability": choice("usable"), **STAGE_2, **STAGE_3})
    state = transport.calls[2][1]
    assert state["earlier_judgments"]["evidence_sufficiency"] == "partial"
    assert state["thesis"] == "Margins expand through 2027"
    assert "earlier_judgments" not in transport.calls[1][1]


def test_no_thesis_omits_thesis_impact():
    result, transport = run({"data_usability": choice("usable"), **STAGE_2, **STAGE_3}, thesis=None)
    assert "thesis_impact" not in transport.calls[2][0]
    assert "thesis_impact" not in result.judgments
    assert result.abstention_reasons == ["no_recorded_thesis"]


def test_budget_refusal_mid_run_is_partial_not_a_crash():
    result, _ = run(
        {"data_usability": choice("partial"), **STAGE_2},
        failures={"event_family": (402, {})},
    )
    assert result.judgments == {"data_usability": "partial"}
    assert result.abstention_reasons == ["budget_skipped"]


def test_provider_down_at_stage_one_yields_no_judgments():
    result, _ = run({}, failures={"data_usability": (529, {})})
    assert result.judgments == {}
    assert result.abstention_reasons == ["classification_unavailable"]


def test_lookahead_exclusions_are_reported():
    transport = ScriptedTransport({"data_usability": choice("unusable")})
    client = JevClient(transport, sleep=lambda _: None)
    result = run_staged(ROOT / "evals/fixtures/packets/08-lookahead", client)
    assert result.excluded_evidence_ids == ["ev-2"]


@pytest.mark.parametrize(
    ("probabilities", "level"),
    [
        ({"0": 0.1, "1": 0.2, "2": 0.6, "3": 0.1, "4": 0.0}, 3),
        ({"0": 0.0, "1": 0.45, "2": 0.1, "3": 0.45, "4": 0.0}, 2),
        ({"0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 1.0}, 5),
    ],
)
def test_score_maps_to_most_probable_level_with_ties_rounding_down(probabilities, level):
    assert score_level(score(probabilities), levels=5) == level


@pytest.mark.parametrize(
    "answer",
    [
        {"type": "score", "probabilities": {"0": 1.0}},
        {"type": "score", "probabilities": {"0": 0.5, "1": 0.5, "x": 0.0, "3": 0.0, "4": 0.0}},
        {"type": "choice", "choice": "a"},
    ],
)
def test_malformed_score_is_rejected(answer):
    assert score_level(answer, levels=5) is None
