"""SEC submissions metadata only; no filing bodies or fabricated publication clocks."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal
from uuid import UUID

from app.models.valuation import Record, UTCTimestamp
from app.providers.transport import Client, Failure
from app.providers.types import Error, Result, digest, identity, timestamp, utc


class Evidence(Record):
    id: str
    source_id: str
    source_type: Literal["filing"] = "filing"
    url: str
    published_at: UTCTimestamp
    known_at: UTCTimestamp
    hash: str
    license_tag: Literal["public-domain:sec-edgar"] = "public-domain:sec-edgar"


@dataclass(frozen=True)
class Filing:
    instrument_id: UUID
    cik: str
    accession: str
    form: str
    filing_date: date
    accepted_at: str
    primary_document: str
    evidence: Evidence


class SEC:
    def __init__(self, client: Client, contact: str, mappings: dict[UUID, str]):
        self.client, self.contact, self.mappings = client, contact, dict(mappings)

    def fetch(self, instrument_id: UUID, start: date, end: date, cutoff=None) -> Result[Filing]:
        result = Result[Filing](requested=(str(start), str(end)))
        if (
            not re.fullmatch(r"[^\r\n]+\s+[^\s@]+@[^\s@]+\.[^\s@]+", self.contact)
            or end < start
            or (end - start).days > 366
        ):
            result.errors.append(Error("configuration", instrument_id))
            return result
        cik = self.mappings.get(instrument_id)
        if not isinstance(cik, str) or not re.fullmatch(r"[0-9]{1,10}", cik) or int(cik) == 0:
            result.errors.append(Error("unresolved_identity", instrument_id))
            return result
        cik = cik.zfill(10)
        if cutoff is not None:
            utc(cutoff)
        headers = {"User-Agent": self.contact}
        budget = self.client.budget()
        seen, excluded = set(), set()

        def consume(columns, received):
            keys = (
                "accessionNumber",
                "form",
                "filingDate",
                "acceptanceDateTime",
                "primaryDocument",
            )
            if not isinstance(columns, dict):
                raise ValueError
            arrays = [columns[key] for key in keys]
            if any(not isinstance(a, list) for a in arrays) or len({len(a) for a in arrays}) != 1:
                raise ValueError
            for accession, form, filed, accepted, document in zip(*arrays, strict=True):
                try:
                    filing_date = date.fromisoformat(filed)
                    if not start <= filing_date <= end:
                        continue
                    if (
                        not isinstance(accession, str)
                        or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession)
                        or not isinstance(form, str)
                        or not form.strip()
                        or not isinstance(document, str)
                        or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", document)
                    ):
                        raise ValueError
                    accepted_at = utc(timestamp(accepted))
                    if timestamp(accepted_at) > received:
                        raise ValueError
                    normalized = {
                        "cik": cik,
                        "accession": accession,
                        "form": form,
                        "filing_date": str(filing_date),
                        "accepted_at": accepted_at,
                        "primary_document": document,
                    }
                    identifier = str(identity(normalized))
                    if cutoff is not None and (
                        received > cutoff or timestamp(accepted_at) > cutoff
                    ):
                        excluded.add(accession)
                        continue
                    if identifier in seen:
                        continue
                    evidence = Evidence(
                        id=identifier,
                        source_id=f"sec:{cik}:{accession}",
                        url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}",
                        published_at=accepted_at,
                        known_at=utc(received),
                        hash=digest(normalized),
                    )
                    result.records.append(
                        Filing(
                            instrument_id,
                            cik,
                            accession,
                            form,
                            filing_date,
                            accepted_at,
                            document,
                            evidence,
                        )
                    )
                    seen.add(identifier)
                except (ValueError, TypeError):
                    result.errors.append(Error("invalid_payload", instrument_id))

        try:
            page, received = self.client.get(
                f"https://data.sec.gov/submissions/CIK{cik}.json", {}, headers, budget, sec=True
            )
            if str(page["cik"]).zfill(10) != cik:
                raise ValueError
            consume(page["filings"]["recent"], received)
            files = page["filings"]["files"]
            if not isinstance(files, list):
                raise ValueError
            names = set()
            for file in files:
                first, last = (
                    date.fromisoformat(file["filingFrom"]),
                    date.fromisoformat(file["filingTo"]),
                )
                if first > last:
                    raise ValueError
                if first > end or last < start:
                    continue
                name = file["name"]
                if (
                    not isinstance(name, str)
                    or not re.fullmatch(rf"CIK{cik}-submissions-[0-9]+\.json", name)
                    or name in names
                ):
                    raise ValueError
                names.add(name)
                historical, received = self.client.get(
                    f"https://data.sec.gov/submissions/{name}", {}, headers, budget, sec=True
                )
                consume(historical, received)
        except Failure as error:
            result.errors.append(Error(error.kind, instrument_id))
        except (KeyError, ValueError, TypeError):
            result.errors.append(Error("invalid_payload", instrument_id))
        result.excluded = tuple(sorted(excluded))
        result.complete = not result.errors and not excluded
        if result.complete:
            result.covered = result.requested
        return result
