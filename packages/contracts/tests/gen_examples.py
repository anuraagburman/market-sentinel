"""Regenerate examples/*.json from one valid base document per entity.

Each invalid case mutates the valid base to break exactly one invariant, so a failing
test points at the rule that regressed. Run: python packages/contracts/tests/gen_examples.py
"""
import copy
import json
import pathlib

OUT = pathlib.Path(__file__).parent / "examples"


def U(n):
    return f"00000000-0000-4000-8000-{n:012d}"


H = "sha256:" + "a" * 64
T = "2026-09-25T12:00:00Z"

VALID = {
    "portfolio_version": {
        "id": U(1), "tenant_id": U(2), "base_currency": "USD", "imported_at": T,
        "source_hash": H, "status": "confirmed", "confirmed_at": T, "previous_version_id": None,
        "cash": {"amount": "1500.00", "currency": "USD"},
    },
    "position": {
        "portfolio_version_id": U(1), "instrument_id": U(10), "display_symbol": "EXCO",
        "quantity": "40", "cost_basis": None, "currency": "USD",
    },
    "observation": {
        "id": U(20), "instrument_id": U(10), "metric": "close", "value": "101.25", "unit": "USD",
        "feed": "fixture", "session": "regular", "adjustment": "none",
        "observed_at": "2026-09-24T20:00:00Z", "received_at": "2026-09-24T20:00:03Z",
    },
    "evidence": {
        "id": "ev-1", "source_id": "exampleco-ir", "source_type": "company_release",
        "originator": "ExampleCo", "url": "https://example.com/ir/2026-09-24",
        "published_at": "2026-09-24T21:05:00Z", "known_at": "2026-09-24T21:06:10Z",
        "hash": H, "license_tag": "synthetic", "correction_of": None,
    },
    "claim": {
        "id": "cl-1", "statement": "ExampleCo lowered FY2026 revenue guidance to 4.1B USD.",
        "evidence_ids": ["ev-1"], "relation": "supports", "entity": "ExampleCo",
        "metric": "revenue_guidance", "period": "FY2026", "value": "4100000000", "unit": "USD",
        "kind": "fact", "extraction_version": "1.0",
    },
    "event": {
        "id": U(30), "instrument_ids": [U(10)], "event_type": "guidance", "cutoff": T,
        "packet_hash": H, "evidence_ids": ["ev-1"], "claim_ids": ["cl-1"],
        "coverage_gaps": ["no_consensus_estimates"],
    },
    "decision": {
        "schema_version": "1.0", "decision_id": U(40), "event_id": U(30), "as_of": T,
        "horizon": "swing", "packet_hash": H, "evidence_ids": ["ev-1", "ev-2"],
        "versions": {"taxonomy": "1.0", "policy": "1.0", "model": "record-provider-model-id", "calibration": None},
        "judgments": {"data_usability": "usable", "evidence_sufficiency": "partial"},
        "raw_provider_output_ref": "private-object-reference", "research_action": "watch_condition",
        "abstention_reasons": ["missing_expectations_data"], "status": "published",
    },
    "brief": {
        "id": U(50), "portfolio_version_id": U(1), "cutoff": T, "published_at": "2026-09-25T12:04:00Z",
        "status": "ready", "decision_ids": [U(40)],
        "coverage": {"checked_sources": ["sec_edgar", "alpaca_iex"], "failed_sources": []},
        "revision": 1,
    },
    "plan": {
        "id": U(60), "instrument_id": U(10), "thesis_version": 1,
        "thesis": "Margin recovery in FY2027 as input costs normalize.", "thesis_state": "under_review",
        "horizon": "multiweek",
        "conditions": [
            {"kind": "wait", "description": "Do nothing until the macro release and a full session of liquidity.",
             "observable_evidence": "CPI release published and one regular session closed."},
            {"kind": "reduce", "description": "Reduce if the guidance cut reflects demand, not one-off costs.",
             "observable_evidence": "Management commentary attributes the cut to volume declines.",
             "price_reference": {"value": "92.00", "currency": "USD", "source": "user", "as_of": T}},
        ],
        "invalidation": "Gross margin guidance cut for FY2027.", "paper_size": None,
        "revision": 1, "created_at": T,
    },
    "run": {
        "id": U(70), "stage": "publish", "idempotency_key": f"publish:{U(1)}:{T}:1.0", "attempts": 1,
        "state": "succeeded", "error_code": None, "cutoff": T, "created_at": T,
        "finished_at": "2026-09-25T12:04:00Z",
    },
}


def _walk(d, path):
    for key in path[:-1]:
        d = d[key]
    return d, path[-1]


def setk(path, value):
    def f(d):
        parent, key = _walk(d, path)
        parent[key] = value
    return f


def delk(path):
    def f(d):
        parent, key = _walk(d, path)
        del parent[key]
    return f


def both(*fns):
    def f(d):
        for fn in fns:
            fn(d)
    return f


def case(entity, why, fn):
    doc = copy.deepcopy(VALID[entity])
    fn(doc)
    return {"why": why, "doc": doc}


INVALID = {
    "portfolio_version": [
        case("portfolio_version", "confirmed version without confirmed_at", delk(["confirmed_at"])),
        case("portfolio_version", "lowercase currency", setk(["base_currency"], "usd")),
    ],
    "position": [
        case("position", "cost_basis key missing (unknown must be explicit null)", delk(["cost_basis"])),
        case("position", "zero quantity", setk(["quantity"], "0")),
        case("position", "short (negative) quantity", setk(["quantity"], "-40")),
        case("position", "float quantity instead of decimal string", setk(["quantity"], 40.0)),
    ],
    "observation": [
        case("observation", "non-UTC offset timestamp", setk(["observed_at"], "2026-09-24T16:00:00-04:00")),
        case("observation", "feed not stated", delk(["feed"])),
        case("observation", "received_at missing", delk(["received_at"])),
    ],
    "evidence": [
        case("evidence", "known_at missing", delk(["known_at"])),
        case("evidence", "unknown source_type", setk(["source_type"], "rumor")),
    ],
    "claim": [
        case("claim", "claim with no evidence", setk(["evidence_ids"], [])),
        case("claim", "numeric value without unit", delk(["unit"])),
    ],
    "event": [
        case("event", "event with no instrument", setk(["instrument_ids"], [])),
        case("event", "event_type outside taxonomy", setk(["event_type"], "rumor")),
    ],
    "decision": [
        case("decision", "unusable data promoted to investigate_now",
             both(setk(["judgments", "data_usability"], "unusable"), setk(["research_action"], "investigate_now"))),
        case("decision", "abstention without a reason",
             both(setk(["research_action"], "insufficient_evidence"), setk(["abstention_reasons"], []))),
        case("decision", "confidence field smuggled in", setk(["confidence"], 0.92)),
        case("decision", "research_relevance outside 1-5", setk(["judgments", "research_relevance"], 7)),
        case("decision", "judgment label not in taxonomy", setk(["judgments", "primary_context"], "technical")),
        case("decision", "trade action instead of research action", setk(["research_action"], "sell")),
        case("decision", "data_usability stage missing", delk(["judgments", "data_usability"])),
    ],
    "brief": [
        case("brief", "revision 2 without supersedes/change_reason", setk(["revision"], 2)),
        case("brief", "failed source reported as ready",
             setk(["coverage"], {"checked_sources": ["sec_edgar"], "failed_sources": ["news_vendor"]})),
        case("brief", "failed source reported as no_material_change",
             both(setk(["status"], "no_material_change"),
                  setk(["coverage"], {"checked_sources": [], "failed_sources": ["news_vendor"]}))),
    ],
    "plan": [
        case("plan", "model-supplied price level", setk(["conditions", 1, "price_reference", "source"], "model")),
        case("plan", "condition without observable evidence", delk(["conditions", 0, "observable_evidence"])),
        case("plan", "revision without reason", setk(["revision"], 2)),
        case("plan", "calculated price without calculation_id",
             setk(["conditions", 1, "price_reference", "source"], "calculation")),
    ],
    "run": [
        case("run", "failed run without error_code", setk(["state"], "failed")),
        case("run", "negative attempts", setk(["attempts"], -1)),
    ],
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, doc in VALID.items():
        (OUT / f"{name}.valid.json").write_text(json.dumps([doc], indent=2) + "\n")
        (OUT / f"{name}.invalid.json").write_text(json.dumps(INVALID[name], indent=2) + "\n")
    print(f"{len(VALID)} valid, {sum(map(len, INVALID.values()))} invalid cases")


if __name__ == "__main__":
    main()
