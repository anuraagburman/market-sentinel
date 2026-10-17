import importlib.util
import json
from pathlib import Path

from app.judgment.client import JevClient
from app.judgment.stages import run_staged

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("record_jev", ROOT / "scripts/record_jev.py")
record_jev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(record_jev)


def choice(value):
    return {"type": "choice", "choice": value, "probabilities": {value: 1.0}, "confidence": 1.0}


class RetryingThenScripted:
    """Stage 1 is rate-limited, then overloaded, then answers; later stages answer at once."""

    def __init__(self):
        self.failures = [(429, {}), (529, {})]

    def send(self, body):
        asked = json.loads(body)["questions"]
        if "data_usability" in asked and self.failures:
            return self.failures.pop(0)
        answers = {q: choice("unusable") for q in asked}
        return 200, {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 10}}


def test_retries_stay_in_their_stage_file(tmp_path, monkeypatch):
    monkeypatch.setattr(record_jev, "OUT", tmp_path)
    packet = ROOT / "evals/fixtures/packets/01-earnings-no-expectations"
    files = record_jev.StageFiles(RetryingThenScripted(), packet.name)
    run_staged(packet, JevClient(files, sleep=lambda _: None))
    written = sorted(p.name for p in (tmp_path / packet.name).iterdir())
    assert written == ["stage-1.json"]
    record = json.loads((tmp_path / packet.name / "stage-1.json").read_text())
    assert record["stage"] == 1
    assert record["status"] == 200
    assert record["retried_statuses"] == [429, 529]
    assert list(record["request"]["questions"]) == ["data_usability"]
