"""Record live JEV responses for the adversarial packets, for offline replay (T-009).

    uv run --project apps/api python scripts/record_jev.py --dry-run   # sizes and estimated cost only
    uv run --project apps/api python scripts/record_jev.py --live      # spends credit; needs approval

`--live` reads TYPESAFE_API_KEY from the environment and writes one file per packet and stage to
evals/recordings/jev/<packet>/stage-<n>.json. Packets are synthetic; nothing else is sent. Never
imported by tests.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.judgment.client import (  # noqa: E402
    MODEL,
    PRICE_PER_INPUT_TOKEN,
    JevClient,
    LiveTransport,
    RecordingTransport,
    encode_request,
)
from app.judgment.questions import QUESTIONS_VERSION, questions_hash, render_stage  # noqa: E402
from app.judgment.stages import run_staged  # noqa: E402
from app.judgment.state import build_state  # noqa: E402

PACKETS = ROOT / "evals/fixtures/packets"
OUT = ROOT / "evals/recordings/jev"


class StageFiles:
    """Names each successive call of one packet run stage-1.json, stage-2.json, ..."""

    def __init__(self, live, packet: str):
        self.live = live
        self.packet = packet
        self.stage = 0

    def send(self, body):
        self.stage += 1
        meta = {
            "packet": self.packet,
            "stage": self.stage,
            "model_requested": MODEL,
            "questions_version": QUESTIONS_VERSION,
            "questions_hash": questions_hash(),
            "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path = OUT / self.packet / f"stage-{self.stage}.json"
        return RecordingTransport(self.live, path, meta).send(body)


def dry_run(packets):
    total = 0
    for packet in packets:
        state = build_state(packet).state
        for stage in (1, 2, 3):
            size = len(encode_request(state, render_stage(stage)))
            total += size
            print(f"{packet.name:32} stage {stage}: {size:6} bytes")
    tokens = total // 4  # rough upper estimate for English JSON
    print(
        f"~{tokens} input tokens at most -> ~${Decimal(tokens) * PRICE_PER_INPUT_TOKEN:.6f}"
    )


def live(packets):
    transport = LiveTransport()
    spent, tokens = Decimal(0), 0
    for packet in packets:
        client = JevClient(StageFiles(transport, packet.name))
        result = run_staged(packet, client)
        spent += result.cost
        tokens += result.input_tokens
        print(
            f"{packet.name:32} {json.dumps(result.judgments)} {result.abstention_reasons}"
        )
    print(f"model {MODEL}: {tokens} input tokens, ${spent:.6f}")


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = parser.parse_args()
    packets = sorted(p for p in PACKETS.iterdir() if p.is_dir())
    dry_run(packets) if args.dry_run else live(packets)


if __name__ == "__main__":
    main()
