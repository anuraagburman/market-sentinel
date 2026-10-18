"""Record the plain persona once. --dry-run never constructs a provider client."""

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from app.judgment.client import ReplayMiss, request_hash  # noqa: E402
from app.policy.envelope import decide  # noqa: E402
from evals.harness.persona import (  # noqa: E402
    INPUT_PRICE,
    MODEL,
    OUTPUT_PRICE,
    PersonaClient,
    PersonaTransport,
    persona_request,
)
from scripts.record_jev import PACKETS, SESSION_CLOSE, fixture_valuation  # noqa: E402

OUT = ROOT / "evals/recordings/persona"


class StageFiles:
    def __init__(self, inner, packet, root=OUT):
        self.inner, self.packet, self.root = inner, packet, root
        self.stage = 0
        self.cost = Decimal(0)

    def send(self, body):
        self.stage += 1
        path = self.root / self.packet / f"stage-{self.stage}.json"
        if path.exists():
            record = json.loads(path.read_text())
            if record["request_hash"] != request_hash(body):
                raise ReplayMiss(
                    f"{self.packet}/stage-{self.stage}: request hash changed"
                )
            return record["status"], record["response"]
        status, response = self.inner.send(body)
        record = {
            "packet": self.packet,
            "stage": self.stage,
            "request_hash": request_hash(body),
            "request": json.loads(body),
            "persona_request": persona_request(body),
            "status": status,
            "response": response,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as output:
            output.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
        usage = response.get("usage") or {}
        self.cost += (
            usage.get("input_tokens", 0) * INPUT_PRICE
            + usage.get("output_tokens", 0) * OUTPUT_PRICE
        )
        return status, response


class DryTransport:
    """Use conservative valid placeholder answers to exercise all reachable stages."""

    def __init__(self):
        self.calls = self.bytes = 0

    def send(self, body):
        payload = persona_request(body)
        size = len(json.dumps(payload, sort_keys=True).encode())
        self.calls += 1
        self.bytes += size
        source = json.loads(body)
        answers = {}
        for key in source["questions"]:
            prop = payload["output_config"]["format"]["schema"]["properties"][key]
            value = "partial" if key == "data_usability" else prop["enum"][0]
            if type(value) is int:
                answers[key] = {
                    "type": "score",
                    "probabilities": {
                        str(i): int(i + 1 == value)
                        for i in range(len(prop["enum"]) - 1)
                    },
                }
            else:
                answers[key] = {"type": "choice", "choice": value}
        print(f"  stage {self.calls}: {size} bytes")
        return 200, {
            "model": MODEL,
            "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = parser.parse_args()
    messages = None
    if args.live:
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise RuntimeError("live persona forbidden under pytest")
        import anthropic

        messages = anthropic.Anthropic(max_retries=0).messages
    valuation = fixture_valuation()
    calls = size = 0
    cost = Decimal(0)
    for packet in sorted(p for p in PACKETS.iterdir() if p.is_dir()):
        print(packet.name)
        transport = (
            StageFiles(PersonaTransport(messages), packet.name)
            if args.live
            else DryTransport()
        )
        answer = decide(
            packet,
            valuation,
            PersonaClient(transport),
            expected_session_close=SESSION_CLOSE,
        )
        if args.live:
            cost += transport.cost
            print(answer["research_action"], answer["abstention_reasons"])
        else:
            calls += transport.calls
            size += transport.bytes
    if args.live:
        print(f"New usage cost: ${cost:.6f}")
    else:
        tokens = (size + 3) // 4
        estimate = tokens * INPUT_PRICE + calls * 1024 * OUTPUT_PRICE
        print(
            f"{calls} reachable calls with placeholder answers; {size} request bytes; "
            f"~{tokens} input tokens; estimated cost ~${estimate:.6f} "
            "including maximum output allowance. Token estimate uses bytes/4, not tokenizer; "
            "actual stage count depends on answers. No live calls made."
        )


if __name__ == "__main__":
    main()
