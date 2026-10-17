"""Deterministic integrity gates (policy precedence step 1).

Pure functions over the post-exclusion packet from `build_state`. They run before any model call,
and a model can never raise usability above the strictest cap.
"""

from dataclasses import dataclass

USABILITY = ("unusable", "partial", "usable")  # strictest first


@dataclass(frozen=True)
class GateResult:
    usability_cap: str = "usable"
    reasons: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()


PASS = GateResult()


def split_unadjusted(packet: dict) -> GateResult:
    """An unadjusted close series across a corporate action can't establish a price move."""
    event = packet["event"]
    if event["event_type"] != "corporate_action":
        return PASS
    sessions = {
        o["observed_at"][:10]
        for o in packet["observations"]
        if o["metric"] == "close"
        and o["adjustment"] == "none"
        and o["instrument_id"] in event["instrument_ids"]
    }
    if len(sessions) < 2:
        return PASS
    return GateResult("unusable", ("unusable_input",))
