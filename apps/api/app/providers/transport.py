"""Bounded synchronous JSON boundary. Errors never contain vendor bodies or URLs."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Callable, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ErrorKind = Literal[
    "configuration",
    "authentication",
    "rate_limited",
    "timeout",
    "upstream",
    "invalid_payload",
    "unresolved_identity",
]


class Failure(Exception):
    def __init__(self, kind: ErrorKind):
        self.kind = kind
        super().__init__(kind)


@dataclass(frozen=True)
class Response:
    status: int
    body: str
    headers: dict[str, str]


class Transport(Protocol):
    def __call__(self, url: str, params: dict, headers: dict, timeout: float) -> Response: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, params, headers, timeout):
    """Standard library implementation; redirects cannot forward credentials."""
    req = Request(url + ("?" + urlencode(params) if params else ""), headers=headers)
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as result:
            return Response(result.status, result.read().decode("utf-8"), dict(result.headers))
    except HTTPError as error:
        return Response(error.code, "", dict(error.headers))
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise TimeoutError from None
        raise Failure("upstream") from None
    except TimeoutError:
        raise TimeoutError from None
    except (OSError, UnicodeError):
        raise Failure("upstream") from None


class Limiter:
    """One shared SEC limiter per process, serialized across adapter instances."""

    def __init__(self):
        self.lock = Lock()
        self.last = None

    def wait(self, clock, sleeper, deadline):
        with self.lock:
            now = clock()
            delay = (
                max(0, (self.last + timedelta(seconds=0.2) - now).total_seconds())
                if self.last
                else 0
            )
            if now + timedelta(seconds=delay) >= deadline:
                raise Failure("rate_limited")
            if delay:
                sleeper(delay)
            self.last = clock()


SEC_LIMITER = Limiter()


@dataclass
class Budget:
    deadline: datetime
    pages: int = 0


class Client:
    def __init__(
        self,
        transport: Transport,
        clock: Callable,
        sleeper: Callable,
        jitter: Callable,
        limiter: Limiter = SEC_LIMITER,
    ):
        self.transport, self.clock, self.sleep, self.jitter = transport, clock, sleeper, jitter
        self.limiter = limiter

    def budget(self):
        return Budget(self.clock() + timedelta(seconds=60))

    def get(self, url, params, headers, budget, *, sec=False, array=False):
        if budget.pages >= 100:
            raise Failure("invalid_payload")
        budget.pages += 1
        kind = "timeout"
        for attempt in range(3):
            if sec:
                self.limiter.wait(self.clock, self.sleep, budget.deadline)
            remaining = (budget.deadline - self.clock()).total_seconds()
            if remaining <= 0:
                raise Failure(kind)
            retry_after = None
            try:
                result = self.transport(url, params, headers, min(10, remaining))
            except TimeoutError:
                kind = "timeout"
            else:
                if self.clock() >= budget.deadline:
                    raise Failure("timeout")
                if result.status == 200:
                    try:
                        data = json.loads(
                            result.body,
                            parse_float=Decimal,
                            parse_int=Decimal,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
                        )
                        if not isinstance(data, list if array else dict):
                            raise ValueError
                    except (ValueError, TypeError):
                        raise Failure("invalid_payload") from None
                    return data, self.clock()
                if result.status in (401, 403):
                    raise Failure("authentication")
                if result.status != 429 and not 500 <= result.status <= 599:
                    raise Failure("upstream")
                kind = "rate_limited" if result.status == 429 else "upstream"
                retry_after = next(
                    (v for k, v in result.headers.items() if k.lower() == "retry-after"), None
                )
            if attempt == 2:
                break
            delay = 2**attempt + min(1, max(0, self.jitter()))
            if retry_after is not None:
                try:
                    seconds = float(retry_after)
                    if seconds < 0 or not Decimal(str(seconds)).is_finite():
                        raise ValueError
                except (ValueError, TypeError):
                    try:
                        seconds = max(
                            0, (parsedate_to_datetime(retry_after) - self.clock()).total_seconds()
                        )
                    except (ValueError, TypeError, OverflowError):
                        raise Failure("invalid_payload") from None
                delay = max(delay, seconds)
            if self.clock() + timedelta(seconds=delay) >= budget.deadline:
                raise Failure(kind)
            self.sleep(delay)
        raise Failure(kind)
