"""Synthetic provider boundary tests: no network, credentials, or wall clock."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.providers.transport import Client, Failure, Response


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 1, tzinfo=UTC)
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += timedelta(seconds=seconds)


class HTTP:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params, headers, timeout):
        self.calls.append((url, params.copy(), headers.copy(), timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(body, status=200, headers=None):
    return Response(status, json.dumps(body), headers or {})


def client(*responses):
    clock = Clock()
    http = HTTP(*responses)
    return Client(http, clock, clock.sleep, lambda: 0), http, clock


@pytest.mark.parametrize(
    "status,kind,attempts",
    [
        (401, "authentication", 1),
        (403, "authentication", 1),
        (400, "upstream", 1),
        (429, "rate_limited", 3),
        (500, "upstream", 3),
    ],
)
def test_transport_bounded_retries_and_redaction(status, kind, attempts):
    c, http, _ = client(*(response({"secret": "DO NOT EXPOSE"}, status) for _ in range(3)))
    with pytest.raises(Failure) as error:
        c.get("https://example.test/private?token=secret", {}, {"secret": "key"}, c.budget())
    assert error.value.kind == kind
    assert "secret" not in str(error.value)
    assert len(http.calls) == attempts
    assert all(call[3] <= 10 for call in http.calls)


def test_transport_decimal_timeout_retry_after_and_budget():
    c, http, clock = client(
        TimeoutError("secret"),
        response({}, 429, {"Retry-After": "2"}),
        Response(200, '{"value":0.1234567890123456789}', {}),
    )
    assert c.get("https://example.test", {}, {}, c.budget())[0]["value"] == Decimal(
        "0.1234567890123456789"
    )
    assert len(http.calls) == 3
    assert clock.sleeps == [1, 2]
    c, http, clock = client(response({}, 429, {"Retry-After": "61"}))
    with pytest.raises(Failure, match="rate_limited"):
        c.get("https://example.test", {}, {}, c.budget())
    assert not clock.sleeps
    assert len(http.calls) == 1


@pytest.mark.parametrize("body", ['{"x":NaN}', "{", "null", "[]"])
def test_invalid_payload_never_retried(body):
    c, http, _ = client(Response(200, body, {}))
    with pytest.raises(Failure, match="invalid_payload"):
        c.get("https://example.test", {}, {}, c.budget())
    assert len(http.calls) == 1


from pathlib import Path

from app.providers.alpaca import Alpaca, Symbol
from test_contracts_v1_1 import validator

FIXTURES = Path(__file__).resolve().parents[3] / "evals/fixtures/providers"
ID = UUID(int=1)
START, END = date(2026, 3, 6), date(2026, 3, 9)


def fixture(name):
    return (FIXTURES / f"{name}.json").read_text()


def alpaca(*responses, symbols=None, feed="sip", key="synthetic"):
    c, http, clock = client(*responses)
    clock.now = datetime(2026, 12, 1, tzinfo=UTC)
    mappings = symbols if symbols is not None else [Symbol(ID, "SYN01", START)]
    return Alpaca(c, key, "synthetic", feed, mappings), http, clock


def calendar():
    return Response(200, fixture("calendar"), {})


def bars():
    return Response(200, fixture("bars"), {})


def test_alpaca_calendar_decimal_split_and_schema():
    a, http, clock = alpaca(calendar(), bars())
    result = a.fetch(ID, START, END)
    assert result.complete and not result.errors
    assert result.requested == ("2026-03-06", "2026-03-09")
    assert result.covered == result.requested
    close, volume, split, _ = result.records
    assert close.value == "123.1234567890123456789"
    assert split.value == "61.56172839450617283945"
    assert volume.value == "0"
    assert close.observed_at == "2026-03-06T21:00:00Z"
    assert split.observed_at == "2026-03-09T20:00:00Z"
    assert close.received_at == "2026-12-01T00:00:00Z"
    for record in result.records:
        assert record.feed == "sip" and record.adjustment == "none"
        validator("observation").validate(record.model_dump(mode="json"))
    assert http.calls[1][1]["adjustment"] == "raw"
    assert http.calls[1][1]["asof"] == "-"
    assert http.calls[1][1]["timeframe"] == "1Day"
    replay, _, _ = alpaca(calendar(), bars())
    assert replay.fetch(ID, START, END).records == result.records


@pytest.mark.parametrize("value", [0, -1, "-0.00", None, "NaN", "Infinity", "missing"])
def test_alpaca_rejects_invalid_close_and_reports_gap(value):
    bar = {"t": "2026-03-06T05:00:00Z", "v": 0, "c": value}
    if value == "missing":
        del bar["c"]
    a, _, _ = alpaca(calendar(), response({"bars": {"SYN01": [bar]}, "next_page_token": None}))
    result = a.fetch(ID, START, END)
    assert not result.records and not result.complete
    assert result.covered == ()
    assert result.errors[0].kind == "invalid_payload"


@pytest.mark.parametrize("feed,key", [("unknown", "key"), ("", "key"), ("sip", "")])
def test_alpaca_configuration_no_requests(feed, key):
    a, http, _ = alpaca(feed=feed, key=key)
    assert a.fetch(ID, START, END).errors[0].kind == "configuration"
    assert not http.calls


def test_alpaca_half_day_and_cutoff_exclusion():
    payload = {
        "bars": {"SYN01": [{"t": "2026-11-27T05:00:00Z", "c": 12, "v": 0}]},
        "next_page_token": None,
    }
    a, _, _ = alpaca(calendar(), response(payload))
    result = a.fetch(ID, date(2026, 11, 27), date(2026, 11, 27))
    assert result.records[0].observed_at == "2026-11-27T18:00:00Z"
    assert result.records[0].session == "half_day"
    a, _, _ = alpaca(calendar(), response(payload))
    result = a.fetch(ID, date(2026, 11, 27), date(2026, 11, 27), datetime(2026, 11, 28, tzinfo=UTC))
    assert not result.records
    assert result.excluded == ("2026-11-27",)
    assert not result.complete


def test_alpaca_pagination_partial_replay_and_repeated_token():
    payload = json.loads(fixture("bars"))
    payload["next_page_token"] = "next"
    a, http, _ = alpaca(calendar(), response(payload), response(payload))
    result = a.fetch(ID, START, END)
    assert len(result.records) == 4
    assert not result.complete
    assert result.errors[-1].kind == "invalid_payload"
    assert http.calls[-1][1]["page_token"] == "next"
    a, _, _ = alpaca(calendar(), response(payload), response({}, 403))
    result = a.fetch(ID, START, END)
    assert len(result.records) == 4 and not result.complete
    assert result.errors[-1].kind == "authentication"


def test_alpaca_effective_dated_symbols_and_unresolved_identity():
    identities = [UUID(int=i) for i in range(1, 11)]
    mappings = [Symbol(i, f"SYN{n:02}", START) for n, i in enumerate(identities[:-1], 1)]
    mappings[0] = Symbol(ID, "OLD", START, END)
    mappings.append(Symbol(ID, "NEW", END))

    def page(symbol, timestamp):
        return response(
            {"bars": {symbol: [{"t": timestamp, "c": 10, "v": 0}]}, "next_page_token": None}
        )

    a, http, _ = alpaca(
        calendar(),
        page("OLD", "2026-03-06T05:00:00Z"),
        page("NEW", "2026-03-09T04:00:00Z"),
        symbols=mappings,
    )
    result = a.fetch(ID, START, END)
    assert result.complete
    assert [c[1]["symbols"] for c in http.calls[1:]] == ["OLD", "NEW"]
    for identifier in identities[1:-1]:
        n = identities.index(identifier) + 1
        a, _, _ = alpaca(calendar(), page(f"SYN{n:02}", "2026-03-06T05:00:00Z"), symbols=mappings)
        assert a.fetch(identifier, START, START).complete
    a, _, _ = alpaca(calendar(), symbols=mappings)
    assert a.fetch(identities[-1], START, END).errors[0].kind == "unresolved_identity"
