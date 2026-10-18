import copy
from pathlib import Path

import pytest

from app.judgment.state import build_state
from app.policy.gates import (
    GateResult,
    combine,
    final_usability,
    run_gates,
    sources_missing,
    split_unadjusted,
    stale,
    timestamp_order_invalid,
)

PACKETS = Path(__file__).resolve().parents[3] / "evals/fixtures/packets"
SESSION_CLOSE = "2026-09-25T20:00:00Z"


def packet(name):
    return build_state(PACKETS / name).state["packet"]


def test_split_with_unadjusted_closes_is_unusable():
    result = split_unadjusted(packet("02-split-normalization"))
    assert result.usability_cap == "unusable"
    assert result.reasons == ("unusable_input",)


@pytest.mark.parametrize("adjustment", ["split_adjusted", "split_and_dividend_adjusted"])
def test_adjusted_series_across_a_split_passes(adjustment):
    split = copy.deepcopy(packet("02-split-normalization"))
    for observation in split["observations"]:
        observation["adjustment"] = adjustment
    assert split_unadjusted(split).usability_cap == "usable"


def test_single_unadjusted_close_passes():
    split = copy.deepcopy(packet("02-split-normalization"))
    split["observations"] = split["observations"][:1]
    assert split_unadjusted(split).usability_cap == "usable"


def test_two_unadjusted_closes_of_one_session_pass():
    split = copy.deepcopy(packet("02-split-normalization"))
    first = split["observations"][0]
    split["observations"] = [first, {**first, "id": "duplicate-feed", "value": "100.01"}]
    assert split_unadjusted(split).usability_cap == "usable"


def test_unadjusted_closes_without_a_corporate_action_pass():
    split = copy.deepcopy(packet("02-split-normalization"))
    split["event"]["event_type"] = "earnings"
    assert split_unadjusted(split).usability_cap == "usable"


def test_unadjusted_closes_of_another_instrument_pass():
    split = copy.deepcopy(packet("02-split-normalization"))
    for observation in split["observations"]:
        observation["instrument_id"] = "00000000-0000-4000-8000-000000000999"
    assert split_unadjusted(split).usability_cap == "usable"


def test_one_unadjusted_close_per_instrument_passes():
    split = copy.deepcopy(packet("02-split-normalization"))
    other = "00000000-0000-4000-8000-000000000999"
    split["event"]["instrument_ids"].append(other)
    split["observations"][1]["instrument_id"] = other
    assert split_unadjusted(split).usability_cap == "usable"


@pytest.mark.parametrize("name", ["03-syndicated-single-source", "10-failed-coverage"])
def test_no_observations_without_a_gap_caps_at_partial(name):
    result = sources_missing(packet(name))
    assert result == GateResult("partial", ("no_observations",))


def test_no_observations_with_a_declared_gap_is_critical():
    result = sources_missing(packet("07-injection-in-evidence"))
    assert result.usability_cap == "unusable"
    assert result.reasons == ("unusable_input", "critical_source_missing")


def test_a_gap_with_observations_present_passes():
    assert sources_missing(packet("01-earnings-no-expectations")).usability_cap == "usable"


def test_close_before_the_expected_session_close_is_stale():
    result = stale(packet("05-stale-feed"), SESSION_CLOSE)
    assert result.usability_cap == "partial"
    assert result.effects == ("disable_time_sensitive_readiness",)


def test_close_on_the_expected_session_close_is_fresh():
    assert stale(packet("08-lookahead"), SESSION_CLOSE).usability_cap == "usable"


def test_no_close_is_not_judged_stale():
    assert stale(packet("03-syndicated-single-source"), SESSION_CLOSE).usability_cap == "usable"


def test_staleness_ignores_other_instruments_and_metrics():
    fresh = copy.deepcopy(packet("05-stale-feed"))
    late = {**fresh["observations"][0], "observed_at": SESSION_CLOSE}
    fresh["observations"] += [
        {**late, "id": "other", "instrument_id": "00000000-0000-4000-8000-000000000999"},
        {**late, "id": "volume", "metric": "volume"},
    ]
    assert stale(fresh, SESSION_CLOSE).usability_cap == "partial"


def test_evidence_known_before_published_is_invalid():
    broken = copy.deepcopy(packet("01-earnings-no-expectations"))
    broken["evidence"][0]["known_at"] = "2026-01-01T00:00:00Z"
    result = timestamp_order_invalid(broken)
    assert result == GateResult("unusable", ("unusable_input", "timestamp_order_invalid"))


def test_observation_received_before_observed_is_invalid():
    broken = copy.deepcopy(packet("01-earnings-no-expectations"))
    broken["observations"][0]["received_at"] = "2026-09-25T19:59:59Z"
    assert timestamp_order_invalid(broken).usability_cap == "unusable"


def test_equal_timestamps_are_in_order():
    assert timestamp_order_invalid(packet("01-earnings-no-expectations")).usability_cap == "usable"


def test_combine_takes_the_strictest_cap_and_unions_reasons_and_effects():
    combined = combine(
        [
            GateResult("partial", ("no_observations",), ("disable_time_sensitive_readiness",)),
            GateResult("unusable", ("unusable_input", "critical_source_missing")),
            GateResult("unusable", ("unusable_input",)),
        ]
    )
    assert combined == GateResult(
        "unusable",
        ("no_observations", "unusable_input", "critical_source_missing"),
        ("disable_time_sensitive_readiness",),
    )


@pytest.mark.parametrize(
    ("name", "cap"),
    [
        ("01-earnings-no-expectations", "usable"),
        ("02-split-normalization", "unusable"),
        ("03-syndicated-single-source", "partial"),
        ("04-catalyst-uncertain-response", "usable"),
        ("05-stale-feed", "partial"),
        ("06-contradictory-sources", "usable"),
        ("07-injection-in-evidence", "unusable"),
        ("08-lookahead", "usable"),
        ("09-correction", "usable"),
        ("10-failed-coverage", "partial"),
    ],
)
def test_gate_caps_per_packet(name, cap):
    assert run_gates(packet(name), SESSION_CLOSE).usability_cap == cap


NO_OBSERVATIONS = GateResult("partial", ("no_observations",))
STALE = GateResult("partial", effects=("disable_time_sensitive_readiness",))


@pytest.mark.parametrize(
    ("gates", "jev", "final"),
    [
        (GateResult(), "usable", "usable"),
        (GateResult(), "partial", "partial"),
        (GateResult(), "unusable", "unusable"),
        (STALE, "usable", "partial"),
        (STALE, "unusable", "unusable"),
        (NO_OBSERVATIONS, "usable", "partial"),
        (NO_OBSERVATIONS, "unusable", "partial"),
        (GateResult("unusable", ("unusable_input",)), "usable", "unusable"),
    ],
)
def test_jev_can_lower_but_never_raise_usability_except_no_observations(gates, jev, final):
    assert final_usability(gates, jev) == final
