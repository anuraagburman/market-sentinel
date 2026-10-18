"""Record live JEV responses for the adversarial packets, for offline replay (T-009).

    uv run --project apps/api python scripts/record_jev.py --dry-run   # sizes and estimated cost only
    uv run --project apps/api python scripts/record_jev.py --live      # spends credit; needs approval

`--live` reads TYPESAFE_API_KEY from the environment and runs each packet through `decide()` against
the fixture portfolio, so gates, exposure and the override shape the requests exactly as in production.
A request already recorded is replayed, not re-sent: only new requests spend credit and are written to
evals/recordings/jev/<packet>/stage-<n>.json. Packets are synthetic; nothing else is sent. Tests
import only `StageFiles`, with a fake transport; they never construct LiveTransport.
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
    ReplayTransport,
    encode_request,
    request_hash,
)
from app.judgment.questions import QUESTIONS_VERSION, questions_hash, render_stage  # noqa: E402
from app.judgment.state import build_state  # noqa: E402
from app.domain.valuation import value_portfolio  # noqa: E402
from app.models.valuation import Observation, PortfolioVersion, Position  # noqa: E402
from app.policy.envelope import decide  # noqa: E402

PACKETS = ROOT / "evals/fixtures/packets"
PORTFOLIO = ROOT / "evals/fixtures/portfolio"
OUT = ROOT / "evals/recordings/jev"
SESSION_CLOSE = "2026-09-25T20:00:00Z"  # the fixtures' expected session close


def recorded(packet: str) -> dict:
    folder = OUT / packet
    return ReplayTransport(folder).records if folder.exists() else {}


def fixture_valuation():
    def load(name):
        return json.loads((PORTFOLIO / name).read_text())

    return value_portfolio(
        PortfolioVersion.model_validate(load("portfolio_version.json")),
        tuple(Position.model_validate(p) for p in load("positions.json")),
        tuple(Observation.model_validate(o) for o in load("observations.json")),
        datetime.fromisoformat("2026-09-25T21:00:00+00:00"),
    )


class _Reply:
    """Hands an already-received reply to RecordingTransport, so the record format stays in one place."""

    def __init__(self, status, response):
        self.reply = (status, response)

    def send(self, body):
        return self.reply


class StageFiles:
    """Names each stage of one packet run stage-1.json, stage-2.json, ...

    The client retries by re-sending the identical body; a new body starts the next stage. Only a 200
    is written, with the statuses of earlier failed attempts in `retried_statuses`.
    """

    def __init__(self, live, packet: str, recorded: dict | None = None):
        self.live = live
        self.packet = packet
        self.recorded = recorded or {}
        self.input_tokens = 0
        self.stage = 0
        self.last_body = None
        self.retried_statuses = []

    def send(self, body):
        if body != self.last_body:
            self.stage += 1
            self.last_body = body
            self.retried_statuses = []
        known = self.recorded.get(request_hash(body))
        if known is not None:
            return known["status"], known["response"]
        meta = {
            "packet": self.packet,
            "stage": self.stage,
            "retried_statuses": list(self.retried_statuses),
            "model_requested": MODEL,
            "questions_version": QUESTIONS_VERSION,
            "questions_hash": questions_hash(),
            "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        status, response = self.live.send(body)
        self.retried_statuses.append(status)
        if status != 200:  # a failure must never overwrite a good recording
            return status, response
        path = OUT / self.packet / f"stage-{self.stage}.json"
        RecordingTransport(_Reply(status, response), path, meta).send(body)
        if isinstance(response, dict) and isinstance(response.get("usage"), dict):
            self.input_tokens += response["usage"].get("input_tokens") or 0
        return status, response


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
    valuation = fixture_valuation()
    tokens = 0
    for packet in packets:
        files = StageFiles(transport, packet.name, recorded(packet.name))
        envelope = decide(
            packet, valuation, JevClient(files), expected_session_close=SESSION_CLOSE
        )
        tokens += files.input_tokens
        print(
            f"{packet.name:32} {envelope['research_action']:22} "
            f"{json.dumps(envelope['judgments'])} {envelope['abstention_reasons']}"
        )
    print(
        f"model {MODEL}: {tokens} new input tokens, ${tokens * PRICE_PER_INPUT_TOKEN:.6f}"
    )


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
