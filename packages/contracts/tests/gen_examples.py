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
SHARE = "share of priced value (excludes cash and unpriced positions)"


def calc(value, basis):
    return {"kind": "calculation", "value": value, "basis": basis}


def unavailable(reason):
    return {"kind": "unavailable", "reason": reason}


ISSUE = {
    "id": U(80), "decision_id": U(40),
    "holding": {"instrument_id": U(10), "symbol": "EXCO", "name": "ExampleCo"},
    "observation": {"text": "ExampleCo lowered FY2026 revenue guidance.", "source": "ExampleCo company release",
                    "observed_at": "2026-09-24T21:05:00Z"},
    "interpretation": "The release supports the guidance change; the margin effect is unresolved.",
    "evidence_status": "supported", "exposure": calc("0.488000", SHARE),
    "next_question": "Does the lower outlook change the margin assumption in your thesis?",
    "evidence_ids": ["ev-1", "ev-2"],
}

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
    "valuation": {
        "portfolio_version_id": U(1), "base_currency": "USD", "cutoff": T,
        "positions": [
            {"instrument_id": U(10), "display_symbol": "EXCO", "quantity": "40", "cost_basis": "3600.00",
             "price": {"value": "101.25", "observation_id": U(20), "observed_at": "2026-09-24T20:00:00Z",
                       "feed": "fixture"},
             "market_value": calc("4050.00", "quantity × close"),
             "unrealized_pl": calc("450.00", "market value − total cost basis"),
             "weight": calc("1.000000", SHARE)},
            {"instrument_id": U(11), "display_symbol": None, "quantity": "10", "cost_basis": None, "price": None,
             "market_value": unavailable("no_price"), "unrealized_pl": unavailable("market_value_unavailable"),
             "weight": unavailable("market_value_unavailable")},
        ],
        "totals": {"priced_value": calc("4050.00", "exact sum of available market values, rounded once"),
                   "cash": calc("1500.00", "supplied USD cash"), "total_value": unavailable("positions_unpriced")},
        "coverage": {"positions": 2, "priced": 1, "unpriced": 1, "by_reason": {"no_price": 1}},
    },
    "issue": ISSUE,
    "instrument": {"id": U(10), "name": "ExampleCo", "asset_type": "common_stock", "currency": "USD"},
    "symbol_mapping": {"symbol": "EXCO", "instrument_id": U(10), "valid_from": "2020-01-01", "valid_to": "2026-06-30"},
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
        case("observation", "impossible calendar timestamp", setk(["observed_at"], "2026-99-99T29:99:99Z")),
        case("observation", "February 30", setk(["observed_at"], "2026-02-30T12:00:00Z")),
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
        case("decision", "insufficient evidence promoted to investigate_now",
             both(setk(["judgments", "evidence_sufficiency"], "insufficient"),
                  setk(["research_action"], "investigate_now"))),
    ],
    "brief": [
        case("brief", "revision 2 without supersedes/change_reason", setk(["revision"], 2)),
        case("brief", "failed source reported as ready",
             setk(["coverage"], {"checked_sources": ["sec_edgar"], "failed_sources": ["news_vendor"]})),
        case("brief", "failed source reported as no_material_change",
             both(setk(["status"], "no_material_change"),
                  setk(["coverage"], {"checked_sources": [], "failed_sources": ["news_vendor"]}))),
        case("brief", "no_material_change with empty coverage",
             both(setk(["status"], "no_material_change"),
                  setk(["coverage"], {"checked_sources": [], "failed_sources": []}))),
        case("brief", "pending sources on a ready brief", setk(["coverage", "pending_sources"], ["sec_edgar"])),
        case("brief", "no_material_change carrying an issue",
             both(setk(["status"], "no_material_change"), setk(["issues"], [ISSUE]))),
        case("brief", "more than three issues", setk(["issues"], [ISSUE] * 4)),
        case("brief", "issue that breaks the issue schema", setk(["issues"], [{**ISSUE, "evidence_ids": []}])),
    ],
    "valuation": [
        case("valuation", "money with one fractional digit",
             setk(["positions", 0, "market_value", "value"], "4050.0")),
        case("valuation", "weight with two fractional digits", setk(["positions", 0, "weight", "value"], "1.00")),
        case("valuation", "money with a trailing newline",
             setk(["positions", 0, "market_value", "value"], "4050.00\n")),
        case("valuation", "weight with a trailing newline", setk(["positions", 0, "weight", "value"], "1.000000\n")),
        case("valuation", "money weight in a weight slot", setk(["positions", 0, "weight", "value"], "4050.00")),
        case("valuation", "float amount instead of decimal string",
             setk(["positions", 0, "market_value", "value"], 4050.0)),
        case("valuation", "calculation without basis", delk(["positions", 0, "market_value", "basis"])),
        case("valuation", "unknown unavailable reason", setk(["positions", 1, "market_value", "reason"], "stale_price")),
        case("valuation", "unavailable amount carrying a value (missing is not zero)",
             setk(["positions", 1, "market_value", "value"], "0.00")),
        case("valuation", "price without feed", delk(["positions", 0, "price", "feed"])),
        case("valuation", "price key missing (unpriced must be explicit null)", delk(["positions", 1, "price"])),
        case("valuation", "by_reason key outside market-value reasons",
             setk(["coverage", "by_reason"], {"cost_basis_unknown": 1})),
        case("valuation", "by_reason zero count", setk(["coverage", "by_reason"], {"no_price": 0})),
        case("valuation", "negative coverage count", setk(["coverage", "unpriced"], -1)),
        case("valuation", "non-USD base currency", setk(["base_currency"], "EUR")),
        case("valuation", "offset cutoff", setk(["cutoff"], "2026-09-25T08:00:00-04:00")),
    ],
    "issue": [
        case("issue", "issue with no evidence", setk(["evidence_ids"], [])),
        case("issue", "display text instead of a weight string",
             setk(["exposure", "value"], "48.8% of priced portfolio value")),
        case("issue", "unavailable exposure without a reason code",
             setk(["exposure"], {"kind": "unavailable", "reason": "No price observation at the cutoff."})),
        case("issue", "evidence_status outside the enum", setk(["evidence_status"], "confirmed")),
        case("issue", "non-UUID issue id", setk(["id"], "issue-exco-outlook")),
        case("issue", "decision_id missing", delk(["decision_id"])),
        case("issue", "confidence field smuggled in", setk(["confidence"], 0.8)),
    ],
    "instrument": [
        case("instrument", "symbol used as identity", setk(["id"], "EXCO")),
        case("instrument", "asset_type out of scope", setk(["asset_type"], "etf")),
        case("instrument", "lowercase currency", setk(["currency"], "usd")),
        case("instrument", "empty name", setk(["name"], "")),
    ],
    "symbol_mapping": [
        case("symbol_mapping", "lowercase symbol", setk(["symbol"], "exco")),
        case("symbol_mapping", "untrimmed symbol", setk(["symbol"], " EXCO")),
        case("symbol_mapping", "symbol with a trailing newline", setk(["symbol"], "EXCO\n")),
        case("symbol_mapping", "date with a trailing newline", setk(["valid_from"], "2020-01-01\n")),
        case("symbol_mapping", "impossible date", setk(["valid_from"], "2026-02-30")),
        case("symbol_mapping", "timestamp instead of date", setk(["valid_from"], "2020-01-01T00:00:00Z")),
        case("symbol_mapping", "valid_to key missing (open-ended must be explicit null)", delk(["valid_to"])),
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


# Valid variants that sit next to a rule, so the rule is shown not to over-reject.
EXTRA_VALID = {
    "decision": [
        case("decision", "insufficient evidence abstains",
             both(setk(["judgments", "evidence_sufficiency"], "insufficient"),
                  setk(["research_action"], "insufficient_evidence"))),
        case("decision", "evidence_sufficiency absent does not trigger the gate",
             both(delk(["judgments", "evidence_sufficiency"]), setk(["research_action"], "investigate_now"))),
    ],
    "brief": [
        case("brief", "clean day with checked coverage", setk(["status"], "no_material_change")),
        case("brief", "running with pending sources",
             both(setk(["status"], "running"), setk(["coverage", "pending_sources"], ["news_vendor"]))),
        case("brief", "ready with an issue and empty pending", both(
            setk(["issues"], [ISSUE]), setk(["coverage", "pending_sources"], []))),
    ],
    "valuation": [
        case("valuation", "empty portfolio with unknown cash", both(
            setk(["positions"], []),
            setk(["totals"], {"priced_value": unavailable("no_priced_value"), "cash": unavailable("cash_unknown"),
                              "total_value": unavailable("cash_unknown")}),
            setk(["coverage"], {"positions": 0, "priced": 0, "unpriced": 0, "by_reason": {}}))),
        case("valuation", "negative unrealized P/L and negative-zero rounding", both(
            setk(["positions", 0, "unrealized_pl", "value"], "-125.50"),
            setk(["totals", "cash", "value"], "-0.00"))),
    ],
    "issue": [
        case("issue", "unavailable exposure and no display symbol", both(
            setk(["exposure"], unavailable("no_priced_value")), setk(["holding", "symbol"], None))),
    ],
    "symbol_mapping": [
        case("symbol_mapping", "open-ended mapping with a class-share symbol",
             both(setk(["symbol"], "BRK.B"), setk(["valid_to"], None))),
    ],
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, doc in VALID.items():
        extra = [c["doc"] for c in EXTRA_VALID.get(name, [])]
        (OUT / f"{name}.valid.json").write_text(json.dumps([doc, *extra], indent=2) + "\n")
        (OUT / f"{name}.invalid.json").write_text(json.dumps(INVALID[name], indent=2) + "\n")
    print(f"{len(VALID) + sum(map(len, EXTRA_VALID.values()))} valid, {sum(map(len, INVALID.values()))} invalid cases")


if __name__ == "__main__":
    main()
