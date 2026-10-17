from decimal import Decimal

import pytest

from app.policy.actions import load_policy, priority_index, research_action
from app.policy.exposure import Exposure

POLICY = load_policy()
HELD = Exposure(weight=Decimal("0.10"), held=True)
NOT_HELD = Exposure(weight=Decimal(0), held=False)
JUDGED = {
    "data_usability": "usable",
    "event_family": "earnings",
    "primary_context": "company",
    "novelty": "new",
    "evidence_sufficiency": "sufficient",
    "research_relevance": 5,
}


def act(judgments=None, usability="usable", exposure=HELD, stale=False, thesis=True, policy=POLICY):
    return research_action(
        usability, JUDGED if judgments is None else judgments, exposure, stale, thesis, policy
    )


def test_policy_values_are_provisional_decimals_summing_to_one():
    index = POLICY["priority_index"]
    assert index["provisional"] is True
    assert sum(index["weights"].values()) == Decimal(1)
    thresholds = index["thresholds"]
    assert (
        thresholds["investigate_now"] > thresholds["review_today"] > thresholds["watch_condition"]
    )


def test_unusable_abstains():
    assert act(usability="unusable") == ("insufficient_evidence", "unusable_input")


def test_insufficient_evidence_abstains():
    judged = {**JUDGED, "evidence_sufficiency": "insufficient"}
    assert act(judged) == ("insufficient_evidence", "insufficient_evidence")


@pytest.mark.parametrize("missing", ["event_family", "evidence_sufficiency"])
def test_missing_stage_two_abstains(missing):
    judged = {k: v for k, v in JUDGED.items() if k != missing}
    assert act(judged) == ("insufficient_evidence", "classification_unavailable")


def test_not_held_without_thesis_is_not_material():
    assert act(exposure=NOT_HELD, thesis=False) == ("no_new_material_issue", None)


def test_not_held_with_a_thesis_is_still_ranked():
    assert act(exposure=NOT_HELD, thesis=True)[0] != "no_new_material_issue"


def test_full_position_and_top_relevance_is_investigate_now():
    assert act() == ("investigate_now", None)


def test_stale_data_cannot_investigate_now():
    assert act(stale=True)[0] == "review_today"


def test_partial_usability_caps_at_review_today():
    assert act(usability="partial") == ("review_today", None)


def test_unavailable_exposure_caps_at_watch_condition():
    assert act(exposure=None) == ("watch_condition", None)


def test_low_index_is_watch_then_not_material():
    low = {**JUDGED, "research_relevance": 1, "event_family": "other"}
    small = Exposure(weight=Decimal("0.001"), held=True)
    assert act(low, exposure=small, stale=True) == ("no_new_material_issue", None)
    assert act(low, exposure=small)[0] == "watch_condition"


@pytest.mark.parametrize(
    ("threshold", "action"),
    [
        ("investigate_now", "investigate_now"),
        ("review_today", "review_today"),
        ("watch_condition", "watch_condition"),
    ],
)
def test_index_exactly_at_a_threshold_takes_the_higher_action(threshold, action):
    index = priority_index(JUDGED, HELD, False, POLICY)
    others = {
        "investigate_now": Decimal(2),
        "review_today": Decimal(2),
        "watch_condition": Decimal(2),
    }
    order = ["watch_condition", "review_today", "investigate_now"]
    for name in order[: order.index(threshold)]:
        others[name] = Decimal(0)
    others[threshold] = index
    policy = {**POLICY, "priority_index": {**POLICY["priority_index"], "thresholds": others}}
    assert act(policy=policy) == (action, None)
    others[threshold] = index + Decimal("1e-20")
    assert act(policy=policy)[0] != action


def test_index_inputs_are_normalized():
    # Full position (10%), top relevance, earnings, fresh: every input is 1.
    assert priority_index(JUDGED, HELD, False, POLICY) == Decimal(1)
    double = Exposure(weight=Decimal("0.20"), held=True)
    assert priority_index(JUDGED, double, False, POLICY) == Decimal(1)


def test_unavailable_exposure_drops_exposure_and_relevance_and_renormalizes():
    weights = POLICY["priority_index"]["weights"]
    stale_share = weights["time_sensitivity"] / (
        weights["event_materiality"] + weights["time_sensitivity"]
    )
    assert priority_index(JUDGED, None, True, POLICY) == 1 - stale_share
