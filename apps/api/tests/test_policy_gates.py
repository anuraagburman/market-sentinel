import copy
from pathlib import Path

import pytest

from app.judgment.state import build_state
from app.policy.gates import split_unadjusted

PACKETS = Path(__file__).resolve().parents[3] / "evals/fixtures/packets"


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
