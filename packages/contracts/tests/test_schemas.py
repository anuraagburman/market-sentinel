"""Contract v1 tests: schemas are valid, examples behave, taxonomy and envelope agree."""
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = pathlib.Path(__file__).parent
SCHEMAS = HERE.parent / "schemas"
EXAMPLES = HERE / "examples"
TAXONOMY = HERE.parents[2] / "decisions" / "taxonomy" / "v1.yaml"

ENTITIES = [
    "portfolio_version", "position", "observation", "evidence", "claim",
    "event", "decision", "brief", "plan", "run",
]


def _load(path):
    return json.loads(path.read_text())


_schemas = {p.name: _load(p) for p in SCHEMAS.glob("*.schema.json")}
_registry = Registry().with_resources(
    (s["$id"], Resource.from_contents(s)) for s in _schemas.values()
)


def validator(entity):
    return Draft202012Validator(
        _schemas[f"{entity}.schema.json"],
        registry=_registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def test_date_time_format_is_enforced():
    """jsonschema silently skips date-time unless rfc3339-validator is installed."""
    assert "date-time" in Draft202012Validator.FORMAT_CHECKER.checkers


@pytest.mark.parametrize("name", sorted(_schemas))
def test_schema_is_valid_draft_2020_12(name):
    Draft202012Validator.check_schema(_schemas[name])


def test_every_entity_has_schema_and_examples():
    for entity in ENTITIES:
        assert f"{entity}.schema.json" in _schemas
        assert (EXAMPLES / f"{entity}.valid.json").exists()
        assert (EXAMPLES / f"{entity}.invalid.json").exists()


def _cases(kind):
    for entity in ENTITIES:
        for i, item in enumerate(_load(EXAMPLES / f"{entity}.{kind}.json")):
            label = item["why"] if kind == "invalid" else f"#{i}"
            yield pytest.param(entity, item, id=f"{entity}:{label}")


@pytest.mark.parametrize("entity,doc", list(_cases("valid")))
def test_valid_examples_pass(entity, doc):
    errors = [e.message for e in validator(entity).iter_errors(doc)]
    assert errors == []


@pytest.mark.parametrize("entity,case", list(_cases("invalid")))
def test_invalid_examples_fail(entity, case):
    assert list(validator(entity).iter_errors(case["doc"])), f"accepted: {case['why']}"


def test_taxonomy_matches_decision_envelope():
    """Taxonomy outputs and envelope judgment enums must never drift apart."""
    taxonomy = yaml.safe_load(TAXONOMY.read_text())
    judgments = _schemas["decision.schema.json"]["properties"]["judgments"]["properties"]
    common = _schemas["common.schema.json"]["$defs"]

    assert {d["id"] for d in taxonomy["decisions"]} == set(judgments)
    for d in taxonomy["decisions"]:
        prop = judgments[d["id"]]
        if "$ref" in prop:
            prop = common[prop["$ref"].split("/")[-1]]
        if d["type"] == "score":
            allowed = list(range(prop["minimum"], prop["maximum"] + 1))
        else:
            allowed = prop["enum"]
        assert d["outputs"] == allowed, d["id"]


def test_taxonomy_design_records_complete():
    required = {"id", "version", "owner", "purpose", "type", "outputs", "horizon",
                "required", "rules", "ambiguity_policy", "abstain_when", "calibration_target", "examples"}
    for d in yaml.safe_load(TAXONOMY.read_text())["decisions"]:
        assert required <= d.keys(), f"{d['id']} missing {required - d.keys()}"


def test_no_confidence_or_probability_fields():
    text = json.dumps(_schemas).lower()
    for banned in ('"confidence"', '"probability"', '"win_rate"', '"expected_return"'):
        assert banned not in text
