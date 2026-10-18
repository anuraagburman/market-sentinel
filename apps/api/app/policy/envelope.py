"""Assemble one decision envelope per event: gates -> JEV (if allowed) -> override -> action.

The envelope is validated against decision.schema.json before it is returned, and never patched.
"""

import json
import uuid
from functools import cache
from pathlib import Path

from app.judgment.client import JevClient
from app.judgment.questions import load_taxonomy
from app.judgment.stages import run_staged
from app.judgment.state import build_state
from app.models.valuation import Valuation
from app.policy.actions import load_policy, research_action
from app.policy.exposure import exposure_for
from app.policy.gates import TIME_SENSITIVE, run_gates

SCHEMAS = Path(__file__).resolve().parents[4] / "packages/contracts/schemas"
DECISION_SCHEMA = "https://market-sentinel.local/schemas/decision.schema.json"
DECISION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://market-sentinel.local/decisions")
OUTAGES = {"classification_unavailable", "budget_skipped"}


@cache
def _validator():
    # dev/eval dependencies, as in app.judgment.questions
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schemas = [json.loads(p.read_text()) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
    return Draft202012Validator({"$ref": DECISION_SCHEMA}, registry=registry)


def decide(
    packet_dir: Path,
    valuation: Valuation,
    client: JevClient | None,
    *,
    expected_session_close: str,
    thesis: str | None = None,
    horizon: str = "swing",
    policy: dict | None = None,
) -> dict:
    """`client=None` is the rules-only path. `expected_session_close` comes from the caller (T-008)."""
    policy = policy or load_policy()
    event = json.loads((packet_dir / "event.json").read_text())
    packet = build_state(packet_dir).state["packet"]
    gates = run_gates(packet, expected_session_close)
    exposure = exposure_for(packet["event"], valuation)

    judgments = {"data_usability": gates.usability_cap}
    run_reasons: list[str] = []
    model = "rules-only"
    if client is not None and gates.usability_cap != "unusable":
        result = run_staged(packet_dir, client, thesis, exposure, gates)
        run_reasons = result.abstention_reasons
        # an outage at any stage degrades to gate-only, even after earlier stages answered
        if "data_usability" in result.judgments and not OUTAGES & set(run_reasons):
            judgments, model = result.judgments, result.model
        else:
            model = "unavailable"

    action, action_reason = research_action(
        judgments["data_usability"],
        judgments,
        exposure,
        TIME_SENSITIVE in gates.effects,
        thesis is not None,
        policy,
    )
    reasons = [
        *gates.reasons,
        *(["exposure_unavailable"] if exposure is None else []),
        *run_reasons,
        *([action_reason] if action_reason else []),
    ]
    key = "|".join([event["id"], event["cutoff"], policy["version"], model])
    envelope = {
        "schema_version": "1.0",
        "decision_id": str(uuid.uuid5(DECISION_NAMESPACE, key)),
        "event_id": event["id"],
        "as_of": event["cutoff"],
        "horizon": horizon,
        "packet_hash": event["packet_hash"],
        "evidence_ids": [item["id"] for item in packet["evidence"]],
        "versions": {
            "taxonomy": load_taxonomy()["version"],
            "policy": policy["version"],
            "model": model,
            "calibration": None,
        },
        "judgments": judgments,
        "raw_provider_output_ref": None,  # raw output storage is an ADR-005 follow-up
        "research_action": action,
        "abstention_reasons": list(dict.fromkeys(reasons)),
        "status": "published",
    }
    _validator().validate(envelope)
    return envelope
