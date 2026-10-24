"""Validated, attributed imports. Source files are retained by content hash."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .db import connect, db_path

ISIN = re.compile(r"^IN[A-Z0-9]{10}$")
MAX_BYTES = 5 * 1024 * 1024


class ImportProblem(ValueError):
    pass


class HoldingsProvider(Protocol):
    """A source adapter may discover available statements and ingest one snapshot."""

    def discover(self, scheme_id: str) -> list[dict]: ...

    def ingest(self, data: bytes, **metadata) -> dict: ...


class MarketProvider(Protocol):
    """A source adapter supplies dated, attributed observations."""

    def ingest(self, data: bytes, *, source_url: str) -> dict: ...


class UserCSVHoldingsProvider:
    def discover(self, scheme_id: str) -> list[dict]:
        from .db import rows

        with connect() as db:
            return rows(
                db,
                """SELECT report_date,published_at,source_url,complete,parse_status
                FROM snapshots WHERE scheme_id=? ORDER BY report_date DESC""",
                (scheme_id,),
            )

    def ingest(self, data: bytes, **metadata) -> dict:
        return import_holdings(data, **metadata)


class UserCSVMarketProvider:
    def ingest(self, data: bytes, *, source_url: str) -> dict:
        return import_market(data, source_url=source_url)


def utcnow():
    return datetime.now(UTC).isoformat()


def valid_url(value: str, synthetic=False):
    parsed = urlparse(value)
    if synthetic and parsed.scheme == "sample":
        return value
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
        raise ImportProblem("Source URL must be a public HTTP(S) URL.")
    return value


def parse_date(value: str, name: str):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ImportProblem(f"{name} must be YYYY-MM-DD.") from exc


def number(value: str | None, name: str, *, minimum=0, maximum=None, required=True):
    if value is None or str(value).strip() == "":
        if required:
            raise ImportProblem(f"{name} is required.")
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise ImportProblem(f"{name} must be numeric.") from exc
    if not math.isfinite(result) or result < minimum or (maximum is not None and result > maximum):
        raise ImportProblem(f"{name} is outside its allowed range.")
    return result


def read_csv(data: bytes, required: set[str]):
    if not data or len(data) > MAX_BYTES:
        raise ImportProblem("CSV must be nonempty and at most 5 MB.")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportProblem("CSV must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames and len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ImportProblem("CSV contains duplicate column names.")
    headers = set(reader.fieldnames or [])
    if not required <= headers or None in headers:
        raise ImportProblem(
            f"Missing required CSV columns: {', '.join(sorted(required - headers))}."
        )
    records = list(reader)
    if not records or len(records) > 20000 or any(None in row for row in records):
        raise ImportProblem("CSV has no rows, too many rows, or malformed columns.")
    return records


def check_security(db, row):
    isin = (row.get("isin") or "").strip().upper()
    company = (row.get("company") or "").strip()
    ticker = (row.get("ticker") or "").strip().upper() or None
    if not ISIN.fullmatch(isin) or not company or len(company) > 200:
        raise ImportProblem("Each security needs a well-formed Indian ISIN and company name.")
    existing = db.execute("SELECT * FROM securities WHERE isin=?", (isin,)).fetchone()
    if existing and existing["company"].casefold() != company.casefold():
        raise ImportProblem(
            f"Ambiguous company mapping for {isin}; review identifiers before import."
        )
    if ticker:
        collision = db.execute(
            "SELECT isin FROM securities WHERE ticker=? AND isin<>?", (ticker, isin)
        ).fetchone()
        if collision:
            raise ImportProblem(
                f"Ticker {ticker} maps to multiple ISINs; review identifiers before import."
            )
        if existing and existing["ticker"] and existing["ticker"] != ticker:
            raise ImportProblem(f"Ticker changed for {isin}; review mapping before import.")
    db.execute(
        "INSERT OR IGNORE INTO securities(isin,company,ticker,sector,industry) VALUES(?,?,?,?,?)",
        (
            isin,
            company,
            ticker,
            (row.get("sector") or "").strip() or None,
            (row.get("industry") or "").strip() or None,
        ),
    )
    if ticker:
        if existing and not existing["ticker"]:
            db.execute("UPDATE securities SET ticker=? WHERE isin=?", (ticker, isin))
        db.execute(
            "INSERT OR IGNORE INTO identifier_mappings(isin,ticker,source_url) VALUES(?,?,?)",
            (isin, ticker, row.get("source_url")),
        )
    return isin


def retain(data: bytes, suffix="csv"):
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(os.getenv("RISKORA_UPLOAD_DIR", str(db_path().parent / "uploads"))).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{digest}.{suffix}"
    if not target.exists():
        target.write_bytes(data)
    return digest


def import_holdings(
    data: bytes,
    *,
    scheme_id: str,
    scheme_name: str,
    amc: str,
    report_date: str,
    published_at: str,
    source_url: str,
    complete: bool,
    category: str = "",
    source_kind="user_import",
    availability_basis: str = "publication",
    source_note: str = "",
):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{2,64}", scheme_id):
        raise ImportProblem("Scheme ID must be 2-64 letters, digits, underscores, or hyphens.")
    if not scheme_name.strip() or not amc.strip() or len(scheme_name) > 200 or len(amc) > 200:
        raise ImportProblem("Scheme name and AMC are required (max 200 characters).")
    if source_kind not in {"user_import", "synthetic"}:
        raise ImportProblem("Unsupported source kind.")
    if availability_basis not in {"publication", "observed"}:
        raise ImportProblem("Availability basis must be publication or observed.")
    if source_kind == "synthetic" and availability_basis != "publication":
        raise ImportProblem("Synthetic snapshots use their generated publication date.")
    report = parse_date(report_date, "report_date")
    published = parse_date(published_at, "published_at")
    if report > published or published > date.today():
        raise ImportProblem("Publication date must be after the report date and not in the future.")
    valid_url(source_url, synthetic=source_kind == "synthetic")
    records = read_csv(data, {"isin", "company", "weight"})
    prepared = []
    seen = set()
    for row in records:
        isin = (row.get("isin") or "").strip().upper()
        if isin in seen:
            raise ImportProblem(f"Duplicate holding row for {isin}.")
        seen.add(isin)
        weight = number(row.get("weight"), "weight", minimum=0, maximum=100)
        units = number(row.get("units"), "units", required=False)
        value = number(row.get("market_value"), "market_value", required=False)
        prepared.append((row, weight, units, value))
    total = sum(row[1] for row in prepared)
    if total > 101:
        raise ImportProblem("Holding weights exceed 101%; check percentages and duplicate rows.")
    warnings = []
    if total < 90:
        warnings.append("Weights total below 90%; snapshot treated as incomplete.")
    if availability_basis == "observed":
        warnings.append(
            "Exact publication date is unverified; the availability date is when the file was observed. This snapshot is excluded from comparable labels."
        )
    if source_note.strip():
        warnings.append(source_note.strip())
    effective_complete = bool(complete and total >= 90 and availability_basis == "publication")
    with connect() as db:
        try:
            db.execute("BEGIN")
            old = db.execute(
                "SELECT source_kind,name,amc FROM schemes WHERE id=?", (scheme_id,)
            ).fetchone()
            if old and old["source_kind"] != source_kind:
                raise ImportProblem("Synthetic and real imports cannot share a scheme ID.")
            if old and (
                old["name"].casefold() != scheme_name.strip().casefold()
                or old["amc"].casefold() != amc.strip().casefold()
            ):
                raise ImportProblem(
                    "Scheme ID has a different name or AMC; review the scheme mapping."
                )
            db.execute(
                "INSERT OR IGNORE INTO schemes(id,name,amc,category,source_kind) VALUES(?,?,?,?,?)",
                (
                    scheme_id,
                    scheme_name.strip(),
                    amc.strip(),
                    category.strip() or None,
                    source_kind,
                ),
            )
            for row, *_ in prepared:
                check_security(db, row)
            digest = hashlib.sha256(data).hexdigest()
            cursor = db.execute(
                """INSERT INTO snapshots
                (scheme_id,report_date,published_at,retrieved_at,source_url,file_sha256,
                 source_kind,availability_basis,complete,weight_total,parse_status,warnings)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    scheme_id,
                    report.isoformat(),
                    published.isoformat(),
                    utcnow(),
                    source_url,
                    digest,
                    source_kind,
                    availability_basis,
                    int(effective_complete),
                    total,
                    "parsed",
                    json.dumps(warnings),
                ),
            )
            for row, weight, units, value in prepared:
                db.execute(
                    "INSERT INTO holdings VALUES(?,?,?,?,?)",
                    (cursor.lastrowid, row["isin"].strip().upper(), weight, units, value),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
    retain(data)
    return {
        "snapshot_id": cursor.lastrowid,
        "rows": len(prepared),
        "weight_total": round(total, 4),
        "complete": effective_complete,
        "warnings": warnings,
        "sha256": digest,
    }


def import_market(data: bytes, *, source_url: str, source_kind="user_import"):
    if source_kind not in {"user_import", "synthetic"}:
        raise ImportProblem("Unsupported source kind.")
    valid_url(source_url, synthetic=source_kind == "synthetic")
    records = read_csv(data, {"date", "isin", "company", "close", "volume"})
    prepared = []
    seen = set()
    for row in records:
        day = parse_date((row.get("date") or "").strip(), "date")
        if day > date.today():
            raise ImportProblem("Market observation is in the future.")
        isin = (row.get("isin") or "").strip().upper()
        key = (isin, day.isoformat())
        if key in seen:
            raise ImportProblem(f"Duplicate market observation for {isin} on {day}.")
        seen.add(key)
        close = number(row.get("close"), "close", minimum=0.000001)
        volume = number(row.get("volume"), "volume")
        adjusted = number(
            row.get("adjusted_close"), "adjusted_close", minimum=0.000001, required=False
        )
        row_source = (row.get("source_url") or "").strip() or source_url
        valid_url(row_source, synthetic=source_kind == "synthetic")
        prepared.append((row, day.isoformat(), close, volume, adjusted, row_source))
    with connect() as db:
        try:
            db.execute("BEGIN")
            for row, day, close, volume, adjusted, row_source in prepared:
                isin = check_security(db, row)
                db.execute(
                    """INSERT INTO market_observations
                    (isin,date,close,volume,adjusted_close,source_url,imported_at,source_kind)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (isin, day, close, volume, adjusted, row_source, utcnow(), source_kind),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"rows": len(prepared), "sha256": retain(data)}
