"""Deterministic research-action table over validated judgments (policy precedence step 4).

Only categorical and ordinal judgments are used; JEV probabilities never enter. All arithmetic is Decimal.
"""

from decimal import Decimal
from pathlib import Path

from app.policy.exposure import Exposure

POLICY_PATH = Path(__file__).resolve().parents[4] / "decisions/policies/v1.yaml"
STAGE_2 = ("event_family", "primary_context", "novelty", "evidence_sufficiency")


def load_policy() -> dict:
    import yaml  # dev/eval dependency, as in app.judgment.questions

    policy = yaml.safe_load(POLICY_PATH.read_text())
    index = policy["priority_index"]
    index["exposure_full_weight"] = Decimal(index["exposure_full_weight"])
    for table in ("weights", "thresholds", "event_materiality"):
        index[table] = {k: Decimal(v) for k, v in index[table].items()}
    return policy


def priority_index(
    judgments: dict, exposure: Exposure | None, stale: bool, policy: dict
) -> Decimal:
    config = policy["priority_index"]
    inputs = {
        "event_materiality": config["event_materiality"][judgments["event_family"]],
        "time_sensitivity": Decimal(0 if stale else 1),
    }
    if exposure is not None:  # relevance is only grounded when exposure is known
        inputs["exposure_weight"] = min(
            exposure.weight / config["exposure_full_weight"], Decimal(1)
        )
        if "research_relevance" in judgments:
            inputs["research_relevance"] = Decimal(judgments["research_relevance"] - 1) / 4
    weights = {k: config["weights"][k] for k in inputs}
    return sum(weights[k] * inputs[k] for k in inputs) / sum(weights.values())


def research_action(
    usability: str,
    judgments: dict,
    exposure: Exposure | None,
    stale: bool,
    has_thesis: bool,
    policy: dict,
) -> tuple[str, str | None]:
    """First matching row wins. Returns the action and the abstention reason it adds, if any."""
    if usability == "unusable":
        return "insufficient_evidence", "unusable_input"
    if judgments.get("evidence_sufficiency") == "insufficient":
        return "insufficient_evidence", "insufficient_evidence"
    if any(key not in judgments for key in STAGE_2):
        return "insufficient_evidence", "classification_unavailable"
    if exposure is not None and not exposure.held and not has_thesis:
        return "no_new_material_issue", None

    index = priority_index(judgments, exposure, stale, policy)
    thresholds = policy["priority_index"]["thresholds"]
    if index >= thresholds["investigate_now"] and usability == "usable" and not stale:
        action = "investigate_now"
    elif index >= thresholds["review_today"]:
        action = "review_today"
    elif index >= thresholds["watch_condition"]:
        action = "watch_condition"
    else:
        return "no_new_material_issue", None
    # partial usability never reaches investigate_now above, so it is capped at review_today
    return ("watch_condition" if exposure is None else action), None
