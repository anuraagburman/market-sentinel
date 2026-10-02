"""TypeSafe System One client with record/replay transports.

Pinned to one model version: the `jev-latest` alias moves on release and would silently change
recorded behaviour. Cost is computed here from reported input tokens, never by a model.
"""

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
# docs.typesafe.ai/models (2026-10-02): $0.042 per million input tokens; output tokens are free.
PRICE_PER_INPUT_TOKEN = Decimal("0.042") / Decimal(1_000_000)

RETRYABLE = {0, 429, 500, 502, 503, 504, 529}
BILLING_WORDS = ("credit", "billing", "balance", "payment", "quota")


class JevError(Exception):
    reason = "classification_unavailable"


class JevUnavailable(JevError):
    reason = "classification_unavailable"


class JevBudgetExhausted(JevError):
    reason = "budget_skipped"


class JevConfigError(JevError):
    """Bad key or a request the provider rejects. A bug or setup problem, never retried."""


class ReplayMiss(LookupError):
    """No recording for this exact request. Tests never fall through to the live API."""


class Transport(Protocol):
    def send(self, body: bytes) -> tuple[int, dict]: ...


@dataclass(frozen=True)
class JevResponse:
    model: str
    answers: dict
    input_tokens: int
    cost: Decimal
    request_hash: str
    raw: dict


def encode_request(state: dict, questions: dict, model: str = MODEL) -> bytes:
    body = {"model": model, "state": state, "questions": questions}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def request_hash(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _message(body: dict) -> str:
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message", ""))
    return str(error or body.get("detail") or "")


class LiveTransport:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise RuntimeError(
                "live JEV transport is not allowed under pytest; use ReplayTransport"
            )
        self.api_key = (api_key or os.environ.get("TYPESAFE_API_KEY", "")).strip()
        if not self.api_key:
            raise JevConfigError("TYPESAFE_API_KEY is not set")
        self.timeout = timeout

    def send(self, body: bytes) -> tuple[int, dict]:
        request = urllib.request.Request(
            ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                return reply.status, json.loads(reply.read() or b"{}")
        except urllib.error.HTTPError as error:
            try:
                return error.code, json.loads(error.read() or b"{}")
            except ValueError:
                return error.code, {}
        except (urllib.error.URLError, TimeoutError, ValueError):
            return 0, {}


class RecordingTransport:
    """Wraps a live transport and writes each exchange to `path` for later replay."""

    def __init__(self, inner: Transport, path: Path, meta: dict | None = None):
        self.inner = inner
        self.path = path
        self.meta = meta or {}

    def send(self, body: bytes) -> tuple[int, dict]:
        status, response = self.inner.send(body)
        record = {
            **self.meta,
            "request_hash": request_hash(body),
            "request": json.loads(body),
            "status": status,
            "response": response,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return status, response


class ReplayTransport:
    def __init__(self, root: Path):
        self.records = {}
        for path in sorted(root.rglob("*.json")):
            record = json.loads(path.read_text())
            self.records[record["request_hash"]] = record

    def send(self, body: bytes) -> tuple[int, dict]:
        key = request_hash(body)
        if key not in self.records:
            raise ReplayMiss(key)
        record = self.records[key]
        return record["status"], record["response"]


class JevClient:
    def __init__(
        self,
        transport: Transport,
        *,
        model: str = MODEL,
        max_attempts: int = 3,
        sleep=time.sleep,
        backoff: float = 0.5,
    ):
        self.transport = transport
        self.model = model
        self.max_attempts = max_attempts
        self.sleep = sleep
        self.backoff = backoff

    def ask(self, state: dict, questions: dict) -> JevResponse:
        body = encode_request(state, questions, self.model)
        for attempt in range(1, self.max_attempts + 1):
            status, response = self.transport.send(body)
            if status == 200:
                return self._parse(body, response)
            if status not in RETRYABLE:
                message = _message(response).lower()
                if status == 402 or any(word in message for word in BILLING_WORDS):
                    raise JevBudgetExhausted(f"{status}: {message}")
                raise JevConfigError(f"{status}: {message}")
            if attempt < self.max_attempts:
                self.sleep(self.backoff * 2 ** (attempt - 1) * (1 + random.random()))
        raise JevUnavailable(f"retries exhausted (last status {status})")

    def _parse(self, body: bytes, response: dict) -> JevResponse:
        answers = response.get("answers")
        tokens = response.get("usage", {}).get("input_tokens")
        if not isinstance(answers, dict) or not isinstance(tokens, int):
            raise JevUnavailable("malformed provider response")
        return JevResponse(
            model=response.get("model") or self.model,
            answers=answers,
            input_tokens=tokens,
            cost=tokens * PRICE_PER_INPUT_TOKEN,
            request_hash=request_hash(body),
            raw=response,
        )
