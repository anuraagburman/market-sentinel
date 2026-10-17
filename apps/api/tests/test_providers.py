"""Synthetic provider boundary tests: no network, credentials, or wall clock."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from pathlib import Path

from app.providers.alpaca import Alpaca, Symbol
from test_contracts_v1_1 import validator

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


def sec(*responses, contact="Synthetic research research@example.test", mappings=None):
    from app.providers.sec import SEC
    from app.providers.transport import Limiter

    c, http, clock = client(*responses)
    c.limiter = Limiter()
    return SEC(c, contact, {ID: "1"} if mappings is None else mappings), http, clock


def submissions():
    return Response(200, fixture("submissions"), {})


def history():
    return Response(200, fixture("history"), {})


def test_sec_history_provenance_hash_and_schema():
    a, http, clock = sec(submissions(), history())
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30), clock.now)
    # The historical page was retrieved after this cutoff due to the SEC limiter.
    assert len(result.records) == 1 and len(result.excluded) == 1
    assert not result.complete
    a, http, clock = sec(submissions(), history())
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert result.complete and len(result.records) == 2
    record = result.records[1]
    assert record.cik == "0000000001"
    assert record.accession == "0000000001-26-000001"
    assert record.filing_date == date(2026, 3, 6)
    assert record.accepted_at == "2026-03-05T23:10:00Z"
    assert record.evidence.published_at == record.accepted_at
    assert record.evidence.known_at == "2026-10-01T00:00:00.200000Z"
    assert (
        record.evidence.url
        == "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/synthetic-quarter.htm"
    )
    assert record.evidence.source_id == "sec:0000000001:0000000001-26-000001"
    for record in result.records:
        validator("evidence").validate(record.evidence.model_dump(mode="json"))
    replay, _, _ = sec(submissions(), history())
    assert replay.fetch(ID, date(2026, 1, 1), date(2026, 9, 30)).records == result.records
    assert clock.sleeps == [0.2]
    assert all(call[2]["User-Agent"].startswith("Synthetic") for call in http.calls)


def test_sec_empty_range_and_later_page_failure():
    a, http, _ = sec(submissions())
    result = a.fetch(ID, date(2026, 9, 1), date(2026, 9, 29))
    assert result.complete and not result.records and len(http.calls) == 1
    a, _, _ = sec(submissions(), response({}, 403))
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert not result.complete and len(result.records) == 1
    assert result.errors[0].kind == "authentication"


@pytest.mark.parametrize(
    "change",
    ["missing_acceptance", "bad_time", "parallel_arrays", "unsafe_document", "unsafe_history"],
)
def test_sec_malformed_metadata_visible(change):
    payload = json.loads(fixture("submissions"))
    recent = payload["filings"]["recent"]
    if change == "missing_acceptance":
        recent["acceptanceDateTime"] = [None]
    elif change == "bad_time":
        recent["acceptanceDateTime"] = ["2026-09-30"]
    elif change == "parallel_arrays":
        recent["form"] = []
    elif change == "unsafe_document":
        recent["primaryDocument"] = ["../../secret"]
    else:
        payload["filings"]["files"][0]["name"] = "https://other.test/secret"
    a, _, _ = sec(response(payload), history())
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert not result.complete and result.errors[0].kind == "invalid_payload"


def test_sec_corrections_content_and_accession_change_identity():
    original = json.loads(fixture("submissions"))

    def fetch(payload):
        a, _, _ = sec(response(payload))
        return a.fetch(ID, date(2026, 9, 1), date(2026, 9, 30)).records[0].evidence

    baseline = fetch(original)
    original["filings"]["recent"]["form"] = ["8-K/A"]
    revised = fetch(original)
    assert baseline.hash != revised.hash and baseline.id != revised.id
    assert baseline.source_id == revised.source_id
    original["filings"]["recent"]["accessionNumber"] = ["0000000001-26-000003"]
    assert fetch(original).source_id != revised.source_id


@pytest.mark.parametrize(
    "contact,mappings,kind",
    [
        ("", {ID: "1"}, "configuration"),
        ("missing-contact", {ID: "1"}, "configuration"),
        ("Research test@example.test", {}, "unresolved_identity"),
        ("Research test@example.test", {ID: "../1"}, "unresolved_identity"),
    ],
)
def test_sec_configuration_and_mapping_no_requests(contact, mappings, kind):
    a, http, _ = sec(contact=contact, mappings=mappings)
    assert a.fetch(ID, START, END).errors[0].kind == kind
    assert not http.calls


def test_transport_timeout_exhaustion_and_http_date_retry_after():
    c, http, clock = client(*(TimeoutError("credentials") for _ in range(3)))
    with pytest.raises(Failure, match="timeout"):
        c.get("https://example.test", {}, {}, c.budget())
    assert len(http.calls) == 3 and clock.sleeps == [1, 2]
    c, http, clock = client(
        response({}, 429, {"Retry-After": "Thu, 01 Oct 2026 00:00:03 GMT"}), response({})
    )
    c.get("https://example.test", {}, {}, c.budget())
    assert clock.sleeps == [3]


def test_transport_deadline_spans_pages_and_limits_timeout():
    c, http, clock = client(response({}), response({}))
    budget = c.budget()
    clock.sleep(55)
    c.get("https://example.test", {}, {}, budget)
    assert http.calls[-1][-1] == 5
    clock.sleep(5)
    with pytest.raises(Failure, match="timeout"):
        c.get("https://example.test", {}, {}, budget)
    assert len(http.calls) == 1


@pytest.mark.parametrize(
    "change",
    [{"v": None}, {"v": -1}, {"v": "Infinity"}, {"t": "yesterday"}, {"t": "2026-03-06T05:00:00"}],
)
def test_alpaca_invalid_volume_and_timestamp(change):
    bar = {"t": "2026-03-06T05:00:00Z", "c": 10, "v": 0, **change}
    a, _, _ = alpaca(calendar(), response({"bars": {"SYN01": [bar]}, "next_page_token": None}))
    result = a.fetch(ID, START, END)
    assert not result.records and not result.complete
    assert result.errors[0].kind == "invalid_payload"


@pytest.mark.parametrize(
    "metadata", [{"feed": "iex"}, {"feed": "unknown"}, {"adjustment": "split"}]
)
def test_alpaca_rejects_wrong_series(metadata):
    payload = json.loads(fixture("bars"))
    a, _, _ = alpaca(calendar(), response({**payload, **metadata}))
    result = a.fetch(ID, START, END)
    assert not result.complete and not result.records
    assert result.errors[0].kind == "invalid_payload"


def test_alpaca_missing_session_closed_day_and_pagination_success():
    page = {
        "bars": {"SYN01": [{"t": "2026-03-06T05:00:00Z", "c": 10, "v": 0}]},
        "next_page_token": None,
    }
    a, _, _ = alpaca(calendar(), response(page))
    result = a.fetch(ID, START, END)
    assert result.covered == ("2026-03-06",)
    assert not result.complete
    a, http, _ = alpaca(calendar())
    result = a.fetch(ID, date(2026, 3, 7), date(2026, 3, 8))
    assert result.complete and result.requested == () and len(http.calls) == 1
    a, http, _ = alpaca(response([]))
    assert a.fetch(ID, date(2026, 12, 25), date(2026, 12, 25)).complete
    page["next_page_token"] = "second"
    a, _, _ = alpaca(
        calendar(),
        response(page),
        response(
            {
                "bars": {"SYN01": [{"t": "2026-03-09T04:00:00Z", "c": 5, "v": 0}]},
                "next_page_token": None,
            }
        ),
    )
    result = a.fetch(ID, START, END)
    assert result.complete and len(result.records) == 4


def test_alpaca_page_cap_and_content_identity():
    payload = json.loads(fixture("bars"))
    a, http, _ = alpaca(
        calendar(), *(response({**payload, "next_page_token": str(i)}) for i in range(100))
    )
    result = a.fetch(ID, START, END)
    assert not result.complete and len(http.calls) == 100
    assert result.errors[-1].kind == "invalid_payload"
    first, _, _ = alpaca(calendar(), bars())
    baseline = first.fetch(ID, START, END).records[0]
    payload["bars"]["SYN01"][0]["c"] = "123.12345678901234567890"
    same, _, _ = alpaca(calendar(), response(payload))
    assert same.fetch(ID, START, END).records[0].id == baseline.id
    payload["bars"]["SYN01"][0]["c"] = "123.2"
    changed, _, _ = alpaca(calendar(), response(payload))
    assert changed.fetch(ID, START, END).records[0].id != baseline.id


def test_sec_duplicate_replay_repeated_page_and_ten_ciks():
    payload = json.loads(fixture("submissions"))
    recent = payload["filings"]["recent"]
    a, _, _ = sec(response(payload), response(recent))
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert result.complete and len(result.records) == 1
    payload["filings"]["files"] *= 2
    a, _, _ = sec(response(payload), history())
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert not result.complete and result.errors[-1].kind == "invalid_payload"
    mappings = {UUID(int=i): str(i) for i in range(1, 10)}
    for identifier, cik in mappings.items():
        payload = json.loads(fixture("submissions"))
        payload["cik"] = cik
        a, _, _ = sec(response(payload), mappings=mappings)
        assert a.fetch(identifier, date(2026, 9, 1), date(2026, 9, 30)).complete
    a, _, _ = sec(mappings=mappings)
    assert a.fetch(UUID(int=10), START, END).errors[0].kind == "unresolved_identity"


def test_sec_limiter_shared_across_clients_and_historical_page_cap():
    from app.providers.transport import Limiter

    limiter = Limiter()
    c, http, clock = client(response({}), response({}))
    c.limiter = limiter
    c.get("https://data.sec.gov", {}, {}, c.budget(), sec=True)
    other = Client(http, clock, clock.sleep, lambda: 0, limiter)
    other.get("https://data.sec.gov", {}, {}, other.budget(), sec=True)
    assert clock.sleeps == [0.2]
    payload = json.loads(fixture("submissions"))
    payload["filings"]["files"] = [
        {
            "name": f"CIK0000000001-submissions-{i:03}.json",
            "filingFrom": "2026-01-01",
            "filingTo": "2026-08-31",
        }
        for i in range(100)
    ]
    a, http, _ = sec(response(payload), *(history() for _ in range(100)))
    result = a.fetch(ID, date(2026, 1, 1), date(2026, 9, 30))
    assert not result.complete and len(http.calls) == 100
    assert result.errors[-1].kind == "invalid_payload"


def test_standard_library_socket_timeout_remains_retryable(monkeypatch):
    import app.providers.transport as transport

    class Opener:
        def open(self, request, timeout):
            raise TimeoutError("private URL and credentials")

    monkeypatch.setattr(transport, "build_opener", lambda *_: Opener())
    with pytest.raises(TimeoutError):
        transport.request("https://example.test", {}, {}, 10)


@pytest.mark.parametrize("payload", [{"filings": None}, {"cik": "1", "filings": {"recent": {}}}])
def test_sec_malformed_envelope_returns_typed_failure(payload):
    a, _, _ = sec(response(payload))
    result = a.fetch(ID, START, END)
    assert not result.complete and result.errors[0].kind == "invalid_payload"


@pytest.mark.parametrize("payload", [{}, {"bars": None}, {"bars": {"SYN01": None}}])
def test_alpaca_malformed_envelope_returns_typed_failure(payload):
    a, _, _ = alpaca(calendar(), response(payload))
    result = a.fetch(ID, START, END)
    assert not result.complete and result.errors[0].kind == "invalid_payload"
