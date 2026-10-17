"""Deterministic integrity gates (policy precedence step 1).

Pure functions over the post-exclusion packet from `build_state`. They run before any model call,
and a model can never raise usability above the strictest cap.
"""

from dataclasses import dataclass
from datetime import datetime

USABILITY = ("unusable", "partial", "usable")  # strictest first
TIME_SENSITIVE = "disable_time_sensitive_readiness"


@dataclass(frozen=True)
class GateResult:
    usability_cap: str = "usable"
    reasons: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()


PASS = GateResult()


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _closes(packet: dict) -> list[dict]:
    instruments = packet["event"]["instrument_ids"]
    return [
        o
        for o in packet["observations"]
        if o["metric"] == "close" and o["instrument_id"] in instruments
    ]


def split_unadjusted(packet: dict) -> GateResult:
    """An unadjusted close series across a corporate action can't establish a price move."""
    if packet["event"]["event_type"] != "corporate_action":
        return PASS
    sessions = {o["observed_at"][:10] for o in _closes(packet) if o["adjustment"] == "none"}
    if len(sessions) < 2:
        return PASS
    return GateResult("unusable", ("unusable_input",))


def sources_missing(packet: dict) -> GateResult:
    """No observations: evidence alone backs a hedged brief, unless a coverage gap was declared."""
    if packet["observations"]:
        return PASS
    # shortcut: any coverage gap is critical, upgrade when gaps get typed codes (propose v1.2)
    if packet["coverage_gaps"]:
        return GateResult("unusable", ("unusable_input", "critical_source_missing"))
    return GateResult("partial", ("no_observations",))


def stale(packet: dict, expected_session_close: str) -> GateResult:
    """The latest close predates the session the caller expects; never judged against wall-clock time."""
    closes = _closes(packet)
    if not closes:
        return PASS
    latest = max(_at(o["observed_at"]) for o in closes)
    if latest >= _at(expected_session_close):
        return PASS
    return GateResult("partial", effects=(TIME_SENSITIVE,))


def timestamp_order_invalid(packet: dict) -> GateResult:
    """Something known before it was published, or received before it was observed."""
    if any(_at(e["known_at"]) < _at(e["published_at"]) for e in packet["evidence"]) or any(
        _at(o["received_at"]) < _at(o["observed_at"]) for o in packet["observations"]
    ):
        return GateResult("unusable", ("unusable_input", "timestamp_order_invalid"))
    return PASS


def combine(results: list[GateResult]) -> GateResult:
    """Strictest cap wins; reasons and effects are unioned in first-seen order."""
    return GateResult(
        min((r.usability_cap for r in results), key=USABILITY.index, default="usable"),
        tuple(dict.fromkeys(x for r in results for x in r.reasons)),
        tuple(dict.fromkeys(x for r in results for x in r.effects)),
    )


def run_gates(packet: dict, expected_session_close: str) -> GateResult:
    return combine(
        [
            timestamp_order_invalid(packet),
            split_unadjusted(packet),
            sources_missing(packet),
            stale(packet, expected_session_close),
        ]
    )
