import pytest

from app.judgment.questions import (
    QUESTIONS_VERSION,
    load_taxonomy,
    questions_hash,
    render_question,
    render_stage,
)

TAXONOMY = load_taxonomy()
DECISIONS = {decision["id"]: decision for decision in TAXONOMY["decisions"]}


def test_every_taxonomy_decision_renders():
    for decision_id in DECISIONS:
        question = render_question(decision_id)
        assert question["type"] in {"choice", "score"}
        assert question["instructions"]["task"]


@pytest.mark.parametrize(
    "decision_id", [d for d, spec in DECISIONS.items() if spec["type"] == "choice"]
)
def test_choice_criteria_keys_equal_taxonomy_outputs(decision_id):
    question = render_question(decision_id)
    assert list(question["criteria"]) == [str(o) for o in DECISIONS[decision_id]["outputs"]]
    assert all(question["criteria"].values())


def test_research_relevance_is_five_level_score_without_placeholders():
    question = render_question("research_relevance")
    assert question["type"] == "score"
    assert len(question["criteria"]) == 5
    for level in question["criteria"]:
        assert "TODO" not in level
        assert not any(ch.isdigit() for ch in level), "levels are judged separately; no numbers"


def test_taxonomy_rules_and_untrusted_data_framing_reach_the_model():
    for decision_id, spec in DECISIONS.items():
        instructions = render_question(decision_id)["instructions"]
        assert instructions["rules"] == spec["rules"]
        assert "untrusted" in instructions["data_handling"].lower()


def test_stages_follow_taxonomy_staging():
    staged = {s["stage"]: s["decisions"] for s in TAXONOMY["staging"]}
    for stage, decision_ids in staged.items():
        assert list(render_stage(stage)) == decision_ids


def test_questions_hash_is_stable_and_tracks_wording(monkeypatch):
    from app.judgment import questions

    before = questions_hash()
    assert before == questions_hash()
    assert before.startswith("sha256:")
    assert QUESTIONS_VERSION == "1.0"
    monkeypatch.setitem(questions.TASKS, "novelty", questions.TASKS["novelty"] + " Reworded.")
    assert questions_hash() != before


def test_unknown_decision_raises():
    with pytest.raises(KeyError):
        render_question("not_a_decision")
