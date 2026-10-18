"""Plain persona requests, mapped to the existing staged client protocol."""

import json
from decimal import Decimal

from app.judgment.client import JevClient
from app.judgment.questions import load_taxonomy

MODEL = "claude-haiku-4-5"
SYSTEM = "You are an experienced US-equity trader. Answer the questions using the supplied packet."
INPUT_PRICE = Decimal("1") / 1_000_000
OUTPUT_PRICE = Decimal("5") / 1_000_000


def persona_request(body):
    request = json.loads(body)
    decisions = {d["id"]: d for d in load_taxonomy()["decisions"]}
    properties = {}
    for key in request["questions"]:
        decision = decisions[key]
        values = (
            list(range(1, len(decision["outputs"]) + 1))
            if decision["type"] == "score"
            else [str(v) for v in decision["outputs"]]
        )
        # Null is an explicit refusal to guess, not a made-up taxonomy value.
        properties[key] = {
            "type": ["integer" if decision["type"] == "score" else "string", "null"],
            "enum": [*values, None],
        }
    return {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    {"state": request["state"], "questions": request["questions"]},
                    sort_keys=True,
                ),
            }
        ],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                },
            }
        },
    }


class PersonaTransport:
    """The injected messages interface is fake in tests; Anthropic is imported only in --live."""

    def __init__(self, messages):
        self.messages = messages

    def send(self, body):
        request = persona_request(body)
        reply = self.messages.create(**request)
        raw = reply if isinstance(reply, dict) else reply.model_dump(mode="json")
        response = {"model": MODEL, "usage": raw.get("usage"), "persona_raw": raw}
        try:
            content = raw["content"]
            text = "".join(
                block["text"] for block in content if block["type"] == "text"
            )
            values = json.loads(text)
            properties = request["output_config"]["format"]["schema"]["properties"]
            if not isinstance(values, dict) or set(values) != set(properties):
                raise ValueError("missing decisions")
            answers = {}
            for key, prop in properties.items():
                value = values[key]
                if not any(type(value) is type(v) and value == v for v in prop["enum"]):
                    raise ValueError("invalid enum")
                if value is None:
                    continue
                if type(value) is int:
                    levels = len(prop["enum"]) - 1
                    answers[key] = {
                        "type": "score",
                        "probabilities": {
                            str(i): int(i + 1 == value) for i in range(levels)
                        },
                    }
                else:
                    answers[key] = {"type": "choice", "choice": value}
            response["answers"] = answers
        except (KeyError, TypeError, ValueError):
            # Keep the raw refusal/malformed response. JevClient degrades this to an outage.
            pass
        return 200, response


class PersonaClient(JevClient):
    def __init__(self, transport):
        super().__init__(transport, model=MODEL, max_attempts=1)

    def _parse(self, body, response):
        from dataclasses import replace

        parsed = super()._parse(body, response)
        usage = response["usage"]
        return replace(
            parsed,
            cost=(
                parsed.input_tokens * INPUT_PRICE
                + usage.get("output_tokens", 0) * OUTPUT_PRICE
            ),
        )
