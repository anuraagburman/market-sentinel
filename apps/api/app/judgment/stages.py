"""Run taxonomy v1 as staged JEV calls.

Questions in one call are judged independently, so each stage is its own call and later stages run
only on validated earlier answers. Raw answers (probabilities, confidence) are kept for evaluation but
never enter `judgments`: the decision envelope has no confidence field until calibration is validated.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from app.judgment.client import JevClient, JevConfigError, JevError
from app.judgment.questions import load_taxonomy, render_stage
from app.judgment.state import build_state


@dataclass
class StagedResult:
    judgments: dict = field(default_factory=dict)
    abstention_reasons: list[str] = field(default_factory=list)
    excluded_evidence_ids: list[str] = field(default_factory=list)
    model: str | None = None
    input_tokens: int = 0
    cost: Decimal = Decimal(0)
    raw: dict = field(default_factory=dict)

    def abstain(self, reason: str) -> None:
        if reason not in self.abstention_reasons:
            self.abstention_reasons.append(reason)


def score_level(answer: dict, levels: int) -> int | None:
    """Most probable rubric level (1-based); ties go to the lower level. None when malformed."""
    probabilities = answer.get("probabilities") if answer.get("type") == "score" else None
    if not isinstance(probabilities, dict) or set(probabilities) != {str(i) for i in range(levels)}:
        return None
    best = max(range(levels), key=lambda i: (probabilities[str(i)], -i))
    return best + 1


def _validate(decision: dict, answer: dict | None):
    if not isinstance(answer, dict):
        return None
    if decision["type"] == "score":
        return score_level(answer, len(decision["outputs"]))
    value = answer.get("choice") if answer.get("type") == "choice" else None
    return value if value in [str(o) for o in decision["outputs"]] else None


def _ask(client: JevClient, result: StagedResult, stage: int, state: dict, questions: dict) -> bool:
    """Ask one stage; record valid judgments. False when the stage failed or any answer was invalid."""
    try:
        response = client.ask(state, questions)
    except JevConfigError:
        raise
    except JevError as error:
        result.abstain(error.reason)
        return False
    result.model = response.model
    result.input_tokens += response.input_tokens
    result.cost += response.cost
    result.raw[f"stage_{stage}"] = response.answers
    decisions = {d["id"]: d for d in load_taxonomy()["decisions"]}
    complete = True
    for decision_id in questions:
        value = _validate(decisions[decision_id], response.answers.get(decision_id))
        if value is None:
            result.abstain("invalid_model_output")
            complete = False
        else:
            result.judgments[decision_id] = value
    return complete


def run_staged(packet_dir: Path, client: JevClient, thesis: str | None = None) -> StagedResult:
    built = build_state(packet_dir)
    result = StagedResult(excluded_evidence_ids=built.excluded_evidence_ids)

    if not _ask(client, result, 1, built.state, render_stage(1)):
        return result
    if result.judgments["data_usability"] == "unusable":
        result.abstain("unusable_input")
        return result

    if not _ask(client, result, 2, built.state, render_stage(2)):
        return result

    questions = render_stage(3)
    stage_3_state = {**built.state, "earlier_judgments": dict(result.judgments)}
    if thesis is None:
        questions.pop("thesis_impact")
        result.abstain("no_recorded_thesis")
    else:
        stage_3_state["thesis"] = thesis
    _ask(client, result, 3, stage_3_state, questions)
    return result
