"""Alpaca raw daily bars with explicit feed, local identities and exchange calendar."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.valuation import Observation
from app.providers.transport import Client, Failure
from app.providers.types import Error, Result, decimal, identity, timestamp, utc

NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Symbol:
    instrument_id: UUID
    symbol: str
    valid_from: date
    valid_to: date | None = None  # exclusive


class Alpaca:
    def __init__(self, client: Client, key: str, secret: str, feed: str, symbols):
        self.client, self.key, self.secret, self.feed = client, key, secret, feed
        self.symbols = tuple(symbols)

    def fetch(
        self, instrument_id: UUID, start: date, end: date, cutoff=None
    ) -> Result[Observation]:
        result = Result[Observation]()
        if (
            not self.key
            or not self.secret
            or self.feed not in ("sip", "iex")
            or end < start
            or (end - start).days > 366
        ):
            result.errors.append(Error("configuration", instrument_id))
            return result
        if cutoff is not None:
            utc(cutoff)
        headers = {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}
        budget = self.client.budget()
        covered, excluded, seen = set(), set(), set()
        try:
            calendar, _ = self.client.get(
                "https://paper-api.alpaca.markets/v2/calendar",
                {"start": str(start), "end": str(end)},
                headers,
                budget,
                array=True,
            )
        except Failure as error:
            result.errors.append(Error(error.kind, instrument_id))
            return result
        try:
            sessions = {}
            for row in calendar:
                day = date.fromisoformat(row["date"])
                opening, closing = time.fromisoformat(row["open"]), time.fromisoformat(row["close"])
                if opening.tzinfo or closing.tzinfo or closing <= opening or day in sessions:
                    raise ValueError
                if start <= day <= end:
                    close = datetime.combine(day, closing, NY).astimezone(UTC)
                    sessions[day] = (close, "half_day" if closing < time(16) else "regular")
            result.requested = tuple(str(day) for day in sorted(sessions))
            groups = {}
            for day in sorted(sessions):
                matches = [
                    s
                    for s in self.symbols
                    if s.instrument_id == instrument_id
                    and s.valid_from <= day
                    and (s.valid_to is None or day < s.valid_to)
                ]
                if len(matches) != 1 or not matches[0].symbol.strip():
                    result.errors.append(Error("unresolved_identity", instrument_id))
                    continue
                groups.setdefault(matches[0].symbol, []).append(day)
            for symbol, days in groups.items():
                params = {
                    "symbols": symbol,
                    "timeframe": "1Day",
                    "start": str(min(days)),
                    "end": utc(
                        datetime.combine(max(days) + timedelta(days=1), time(), NY).astimezone(UTC)
                        - timedelta(microseconds=1)
                    ),
                    "feed": self.feed,
                    "adjustment": "raw",
                    "asof": "-",
                    "limit": 10000,
                    "sort": "asc",
                    "currency": "USD",
                }
                tokens = set()
                while True:
                    page, received = self.client.get(
                        "https://data.alpaca.markets/v2/stocks/bars", params, headers, budget
                    )
                    if (
                        page.get("feed", self.feed) != self.feed
                        or page.get("adjustment", "raw") != "raw"
                    ):
                        raise ValueError
                    payload = page["bars"]
                    if not isinstance(payload, dict) or set(payload) - {symbol}:
                        raise ValueError
                    bars = payload.get(symbol, [])
                    if not isinstance(bars, list):
                        raise ValueError
                    for bar in bars:
                        try:
                            market_time = timestamp(bar["t"])
                            day = market_time.astimezone(NY).date()
                            if day not in days:
                                raise ValueError
                            close, session = sessions[day]
                            if close > received:
                                raise ValueError
                            values = [
                                ("close", decimal(bar["c"], positive=True), "USD"),
                                ("volume", decimal(bar["v"]), "shares"),
                            ]
                            if cutoff is not None and (received > cutoff or close > cutoff):
                                excluded.add(str(day))
                                continue
                            for metric, value, unit in values:
                                source = {
                                    "instrument_id": str(instrument_id),
                                    "metric": metric,
                                    "feed": self.feed,
                                    "session": session,
                                    "date": str(day),
                                    "adjustment": "none",
                                    "observed_at": utc(close),
                                    "value": value,
                                }
                                identifier = identity(source)
                                if identifier not in seen:
                                    result.records.append(
                                        Observation(
                                            id=identifier,
                                            instrument_id=instrument_id,
                                            metric=metric,
                                            value=value,
                                            unit=unit,
                                            feed=self.feed,
                                            session=session,
                                            adjustment="none",
                                            observed_at=utc(close),
                                            received_at=utc(received),
                                        )
                                    )
                                    seen.add(identifier)
                            covered.add(str(day))
                        except (KeyError, ValueError, TypeError):
                            result.errors.append(Error("invalid_payload", instrument_id))
                    token = page["next_page_token"]
                    if token is None:
                        break
                    if not isinstance(token, str) or not token or token in tokens:
                        raise ValueError
                    tokens.add(token)
                    params = {**params, "page_token": token}
        except Failure as error:
            result.errors.append(Error(error.kind, instrument_id))
        except (KeyError, ValueError, TypeError):
            result.errors.append(Error("invalid_payload", instrument_id))
        result.covered, result.excluded = tuple(sorted(covered)), tuple(sorted(excluded))
        result.complete = not result.errors and not excluded and set(result.requested) == covered
        return result
