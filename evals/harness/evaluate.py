"""Deterministic descriptive evaluation of frozen fixture recordings."""

import argparse
import json
from collections import Counter

from app.judgment.client import JevClient, ReplayMiss, ReplayTransport
from app.policy.envelope import decide
from evals.harness.persona import PersonaClient
from scripts.record_jev import PACKETS, ROOT, SESSION_CLOSE, fixture_valuation

REPORT = ROOT / "evals/reports/T-010-preliminary.md"


def load_labels():
    return {
        record["packet"]: record
        for path in sorted((ROOT / "evals/labels/v1").glob("*.json"))
        for record in [json.loads(path.read_text())]
    }


class StrictReplay(ReplayTransport):
    def __init__(self, root):
        super().__init__(root)
        self.root = root

    def send(self, body):
        try:
            return super().send(body)
        except ReplayMiss as error:
            raise ReplayMiss(f"{self.root}: stage request {error}") from error


def run_arm(arm, transport_factory=None, recording_root=None):
    valuation = fixture_valuation()
    answers = {}
    for packet in sorted(p for p in PACKETS.iterdir() if p.is_dir()):
        client = None
        if arm != "rules-only":
            root = recording_root or ROOT / "evals/recordings" / (
                "jev" if arm == "JEV" else arm
            )
            transport = (
                transport_factory(packet.name)
                if transport_factory
                else StrictReplay(root / packet.name)
            )
            client = (
                PersonaClient(transport) if arm == "persona" else JevClient(transport)
            )
        answers[packet.name] = decide(
            packet, valuation, client, expected_session_close=SESSION_CLOSE
        )
    return answers


def answer_value(envelope, decision):
    return (
        envelope["research_action"]
        if decision == "research_action"
        else envelope["judgments"].get(decision)
    )


def score(labels, answers, decision):
    result = dict(
        n=0,
        exact=0,
        within_one=0,
        abstentions=0,
        covered=0,
        over=0,
        confusion=Counter(),
    )
    for packet, record in labels.items():
        label = (
            record.get(decision)
            if decision == "research_action"
            else record["labels"][decision]
        )
        if label is None:
            continue
        expected = label.get("value")
        actual = answer_value(answers[packet], decision)
        result["confusion"][
            (
                str(expected) if expected is not None else "abstain",
                str(actual) if actual is not None else "abstain",
            )
        ] += 1
        if expected is None:
            result["abstentions"] += 1
            result["covered"] += actual is None
        else:
            result["n"] += 1
            result["exact"] += type(expected) is type(actual) and expected == actual
            result["over"] += actual is None
            result["within_one"] += (
                type(expected) is int
                and type(actual) is int
                and abs(expected - actual) <= 1
            )
    return result


def policy_bypasses(arms):
    return [
        f"{arm}/{packet}: {answer['research_action']}"
        for arm, answers in arms.items()
        for packet, answer in answers.items()
        if packet.startswith(("02-", "07-"))
        and answer["research_action"] != "insufficient_evidence"
    ]


def render_report(labels, arms):
    failures = policy_bypasses(arms)
    checks = sum(
        name.startswith(("02-", "07-")) for answers in arms.values() for name in answers
    )
    lines = [
        "# T-010 preliminary evaluation",
        "",
        f"Policy bypass: provisional {len(failures)}/{checks} failures (release gate).",
        *failures,
        "",
        "All metrics are provisional (ADR-005); synthetic n=10, one labeler, "
        "no calibration or investment-performance claims. Abstention coverage checks presence, "
        "not agreement on the abstention reason. Missing judgments are abstentions.",
        "",
    ]
    decisions = [*next(iter(labels.values()))["labels"], "research_action"]
    for arm, answers in arms.items():
        lines += [f"## {arm}", ""]
        for decision in decisions:
            s = score(labels, answers, decision)
            limited = decision in {
                "primary_context",
                "thesis_impact",
                "interpretation_conflict",
            }
            description = (
                "refusal-to-guess check only; exact" if limited else "agreement"
            )
            lines += [
                f"### {decision}: provisional",
                "",
                f"provisional {description}: {s['exact']}/{s['n']}; "
                f"abstention coverage: {s['covered']}/{s['abstentions']}; "
                f"over-abstention: {s['over']}/{s['n']}.",
                "",
            ]
            if decision == "research_relevance":
                lines += [f"provisional within ±1: {s['within_one']}/{s['n']}.", ""]
            columns = sorted({actual for _, actual in s["confusion"]} | {"abstain"})
            rows = sorted({expected for expected, _ in s["confusion"]})
            lines += [
                "Confusion counts (provisional; label rows, arm columns):",
                "",
                "| label | " + " | ".join(columns) + " |",
                "|---|" + "---|" * len(columns),
            ]
            for row in rows:
                lines += [
                    f"| {row} | "
                    + " | ".join(str(s["confusion"][(row, col)]) for col in columns)
                    + " |"
                ]
            lines += [""]
        lines += ["### Packet answers", ""]
        for packet, answer in answers.items():
            lines += [
                f"- {packet}: `{json.dumps(answer['judgments'], sort_keys=True)}`; "
                f"action={answer['research_action']}; "
                f"abstentions={','.join(answer['abstention_reasons']) or 'none'}."
            ]
            if arm == "JEV":
                for path in sorted(
                    (ROOT / "evals/recordings/jev" / packet).glob("stage-*.json")
                ):
                    record = json.loads(path.read_text())
                    lines += [
                        f"  - {path.stem} raw (uncalibrated): "
                        f"`{json.dumps(record['response'].get('answers'), sort_keys=True)}`"
                    ]
        lines += [""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    arms = {arm: run_arm(arm) for arm in ("rules-only", "persona", "JEV")}
    report = render_report(load_labels(), arms)
    if args.check:
        if not REPORT.exists() or REPORT.read_text() != report:
            raise SystemExit("Evaluation report changed; regenerate and review it")
    else:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report)
    if policy_bypasses(arms):
        raise SystemExit("Policy bypass: release gate failed")


if __name__ == "__main__":
    main()
