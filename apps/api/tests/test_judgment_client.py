import json
from decimal import Decimal

import pytest

from app.judgment.client import (
    MODEL,
    JevBudgetExhausted,
    JevClient,
    JevConfigError,
    JevUnavailable,
    LiveTransport,
    RecordingTransport,
    ReplayMiss,
    ReplayTransport,
    encode_request,
    request_hash,
)

QUESTIONS = {"q": {"type": "choice", "instructions": "Pick", "criteria": {"a": "A", "b": "B"}}}
STATE = {"packet": {"cutoff": "2026-09-25T21:00:00Z"}}
OK = {
    "model": "jev-1.13.0",
    "answers": {"q": {"type": "choice", "choice": "a", "probabilities": {"a": 0.9, "b": 0.1}}},
    "usage": {"input_tokens": 2000, "output_tokens": 0},
}


class FakeTransport:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []

    def send(self, body):
        self.bodies.append(body)
        return self.replies.pop(0)


def client(*replies, attempts=3):
    return JevClient(FakeTransport(*replies), sleep=lambda _: None, max_attempts=attempts)


def test_success_returns_answers_model_tokens_and_cost():
    response = client((200, OK)).ask(STATE, QUESTIONS)
    assert response.answers["q"]["choice"] == "a"
    assert response.model == "jev-1.13.0"
    assert response.input_tokens == 2000
    assert response.cost == Decimal("0.000084")


def test_request_pins_model_and_is_canonical():
    fake = FakeTransport((200, OK))
    JevClient(fake, sleep=lambda _: None).ask(STATE, QUESTIONS)
    body = json.loads(fake.bodies[0])
    assert body["model"] == MODEL == "jev-1.13.0"
    assert fake.bodies[0] == encode_request(STATE, QUESTIONS)
    assert request_hash(fake.bodies[0]).startswith("sha256:")


def test_retries_rate_limit_and_overload_then_succeeds():
    response = client((429, {}), (529, {}), (200, OK)).ask(STATE, QUESTIONS)
    assert response.answers["q"]["choice"] == "a"


def test_rate_limit_mentioning_quota_is_retried_not_budget():
    response = client((429, {"error": {"message": "rate quota exceeded"}}), (200, OK)).ask(
        STATE, QUESTIONS
    )
    assert response.input_tokens == 2000


def test_exhausted_retries_become_classification_unavailable():
    with pytest.raises(JevUnavailable) as raised:
        client((529, {}), (503, {}), (0, {})).ask(STATE, QUESTIONS)
    assert raised.value.reason == "classification_unavailable"


@pytest.mark.parametrize(
    "reply",
    [(402, {}), (403, {"error": {"message": "Insufficient credit balance"}})],
)
def test_billing_refusal_becomes_budget_skipped_without_retry(reply):
    with pytest.raises(JevBudgetExhausted) as raised:
        client(reply).ask(STATE, QUESTIONS)
    assert raised.value.reason == "budget_skipped"


@pytest.mark.parametrize("status", [401, 403, 422])
def test_configuration_errors_are_not_retried(status):
    with pytest.raises(JevConfigError):
        client((status, {"error": {"message": "nope"}})).ask(STATE, QUESTIONS)


def test_malformed_success_body_is_unavailable():
    with pytest.raises(JevUnavailable):
        client((200, {"model": "jev-1.13.0"})).ask(STATE, QUESTIONS)


def test_recording_then_replay_round_trips(tmp_path):
    recorder = RecordingTransport(FakeTransport((200, OK)), tmp_path / "rec.json")
    body = encode_request(STATE, QUESTIONS)
    assert recorder.send(body) == (200, OK)
    replay = ReplayTransport(tmp_path)
    assert replay.send(body) == (200, OK)


def test_replay_miss_raises_and_never_goes_live(tmp_path):
    with pytest.raises(ReplayMiss):
        ReplayTransport(tmp_path).send(encode_request(STATE, QUESTIONS))


def test_live_transport_refuses_to_exist_under_pytest():
    with pytest.raises(RuntimeError):
        LiveTransport(api_key="test-key")
