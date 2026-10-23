from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import statistics
import time
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .portfolio_risk import AnalyzeRequest, analyze_portfolio

logger = logging.getLogger("institutional_predictor")
load_dotenv(Path(__file__).with_name(".env"))
DATABASE_PATH = Path(
    os.getenv("IIP_DATABASE_PATH", Path(__file__).with_name("iip.sqlite3"))
)
SEC_BASE = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
CIK_PATTERN = re.compile(r"^\d{1,10}$")
TICKER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9.-]{0,9}$")
SEC_CACHE: dict[str, Any] = {}
SEC_REQUEST_LOCK = Lock()
LAST_SEC_REQUEST = 0.0


class ManagerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cik: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Manager name is required.")
        return value

    @field_validator("cik")
    @classmethod
    def clean_cik(cls, value: str) -> str:
        value = value.strip()
        if not CIK_PATTERN.fullmatch(value):
            raise ValueError("CIK must contain 1 to 10 digits.")
        return value.zfill(10)


class MarketScreenRequest(BaseModel):
    ticker: str
    fund_size: float = Field(gt=0)
    target_position_percent: float = Field(gt=0, le=100, default=2)
    minimum_market_cap: float = Field(ge=0, default=1_000_000_000)
    minimum_adtv: float = Field(ge=0, default=5_000_000)
    maximum_five_day_volume_fraction: float = Field(gt=0, le=1, default=0.10)

    @field_validator("ticker")
    @classmethod
    def clean_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not TICKER_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid US stock ticker.")
        return value


def get_sec_user_agent() -> str:
    return os.getenv("IIP_SEC_USER_AGENT", "").strip()


def require_sec_user_agent() -> str:
    value = get_sec_user_agent()
    if not value or "@" not in value:
        raise HTTPException(
            status_code=503,
            detail=(
                "SEC access is not configured. Set IIP_SEC_USER_AGENT to an app name "
                "and monitored contact email, then restart the backend."
            ),
        )
    return value


def throttle_sec_requests() -> None:
    global LAST_SEC_REQUEST
    with SEC_REQUEST_LOCK:
        delay = 0.11 - (time.monotonic() - LAST_SEC_REQUEST)
        if delay > 0:
            time.sleep(delay)
        LAST_SEC_REQUEST = time.monotonic()


def fetch_json(url: str, user_agent: str) -> dict[str, Any]:
    throttle_sec_requests()
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, TimeoutError) as error:
        logger.exception("SEC request failed for %s", url)
        raise HTTPException(
            status_code=502,
            detail=f"SEC data request failed: {error}",
        ) from error


def fetch_text(url: str, user_agent: str) -> str:
    throttle_sec_requests()
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as error:
        logger.exception("SEC document request failed for %s", url)
        raise HTTPException(
            status_code=502,
            detail=f"SEC filing document request failed: {error}",
        ) from error


def database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS managers (
            cik TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            added_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS filings (
            accession TEXT PRIMARY KEY,
            manager_cik TEXT NOT NULL REFERENCES managers(cik) ON DELETE CASCADE,
            form TEXT NOT NULL,
            filed_at TEXT NOT NULL,
            report_date TEXT NOT NULL,
            primary_document TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS holdings (
            accession TEXT NOT NULL REFERENCES filings(accession) ON DELETE CASCADE,
            cusip TEXT NOT NULL,
            issuer TEXT NOT NULL,
            title_of_class TEXT NOT NULL,
            value_thousands REAL NOT NULL,
            shares REAL NOT NULL,
            share_type TEXT NOT NULL,
            put_call TEXT,
            PRIMARY KEY (accession, cusip, title_of_class, put_call)
        );
        """
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def filing_rows(submissions: dict[str, Any]) -> list[dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    rows: list[dict[str, str]] = []
    seen_periods: set[str] = set()
    candidates = sorted(
        range(len(forms)),
        key=lambda index: (
            recent.get("reportDate", [""] * len(forms))[index],
            recent.get("filingDate", [""] * len(forms))[index],
        ),
        reverse=True,
    )
    for index in candidates:
        form = forms[index]
        report_date = recent.get("reportDate", [""] * len(forms))[index]
        if (
            form not in {"13F-HR", "13F-HR/A"}
            or not report_date
            or report_date in seen_periods
        ):
            continue
        accession = recent["accessionNumber"][index]
        rows.append(
            {
                "accession": accession,
                "form": form,
                "filed_at": recent["filingDate"][index],
                "report_date": report_date,
                "primary_document": recent["primaryDocument"][index],
            }
        )
        seen_periods.add(report_date)
        if len(rows) == 4:
            break
    return rows


def sec_filing_url(cik: str, accession: str, primary_document: str) -> str:
    return (
        f"{SEC_ARCHIVES}/{int(cik)}/{accession.replace('-', '')}/"
        f"{quote(primary_document)}"
    )


def extract_information_table(
    cik: str, accession: str, primary_document: str, user_agent: str
) -> list[dict[str, Any]]:
    cik_number = str(int(cik))
    accession_path = accession.replace("-", "")
    directory_url = f"{SEC_ARCHIVES}/{cik_number}/{accession_path}/index.json"
    directory = fetch_json(directory_url, user_agent)
    documents = directory.get("directory", {}).get("item", [])
    table_name = next(
        (
            item["name"]
            for item in documents
            if item.get("name", "").lower().endswith(".xml")
            and "infotable" in item.get("name", "").lower()
        ),
        None,
    )
    if table_name is None:
        primary = next(
            (item for item in documents if item.get("name") == primary_document),
            None,
        )
        if primary and primary_document.lower().endswith(".xml"):
            table_name = primary_document
    if table_name is None:
        return []
    filing_url = f"{SEC_ARCHIVES}/{cik_number}/{accession_path}/{quote(table_name)}"
    content = fetch_text(filing_url, user_agent)
    root = ET.fromstring(content)
    results = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "infoTable":
            continue
        fields: dict[str, str] = {}
        for child in node.iter():
            fields.setdefault(child.tag.rsplit("}", 1)[-1], (child.text or "").strip())
        cusip = fields.get("cusip", "")
        if not cusip:
            continue
        results.append(
            {
                "cusip": cusip,
                "issuer": fields.get("nameOfIssuer", "Unknown issuer"),
                "title_of_class": fields.get("titleOfClass", ""),
                "value_thousands": float(fields.get("value", "0") or 0),
                "shares": float(fields.get("sshPrnamt", "0") or 0),
                "share_type": fields.get("sshPrnamtType", ""),
                "put_call": fields.get("putCall") or None,
            }
        )
    return results


def refresh_manager(cik: str, user_agent: str) -> dict[str, Any]:
    submissions = fetch_json(f"{SEC_BASE}/submissions/CIK{cik}.json", user_agent)
    discovered_name = submissions.get("name", f"CIK {cik}")
    records = filing_rows(submissions)
    saved_filing_count = 0
    total_holding_count = 0
    with closing(database()) as connection:
        existing = connection.execute(
            "SELECT name FROM managers WHERE cik = ?", (cik,)
        ).fetchone()
        if existing and existing["name"]:
            discovered_name = existing["name"]
        else:
            connection.execute(
                "INSERT OR IGNORE INTO managers (cik, name, added_at) VALUES (?, ?, ?)",
                (cik, discovered_name, datetime.now(UTC).isoformat()),
            )
        for filing in records:
            is_new = connection.execute(
                "SELECT 1 FROM filings WHERE accession = ?",
                (filing["accession"],),
            ).fetchone()
            if is_new:
                continue
            holdings = extract_information_table(
                cik, filing["accession"], filing["primary_document"], user_agent
            )
            connection.execute(
                """
                DELETE FROM filings
                WHERE manager_cik = ? AND report_date = ? AND accession != ?
                """,
                (cik, filing["report_date"], filing["accession"]),
            )
            connection.execute(
                """
                INSERT INTO filings
                (accession, manager_cik, form, filed_at, report_date, primary_document)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    filing["accession"],
                    cik,
                    filing["form"],
                    filing["filed_at"],
                    filing["report_date"],
                    filing["primary_document"],
                ),
            )
            connection.executemany(
                """
                INSERT INTO holdings
                (accession, cusip, issuer, title_of_class, value_thousands,
                 shares, share_type, put_call)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        filing["accession"],
                        item["cusip"],
                        item["issuer"],
                        item["title_of_class"],
                        item["value_thousands"],
                        item["shares"],
                        item["share_type"],
                        item["put_call"],
                    )
                    for item in holdings
                ],
            )
            saved_filing_count += 1
            total_holding_count += len(holdings)
        connection.commit()
    return {
        "cik": cik,
        "manager": discovered_name,
        "found_filings": len(records),
        "new_filings": saved_filing_count,
        "new_holdings": total_holding_count,
    }


def get_ticker_directory(user_agent: str) -> dict[str, str]:
    if "tickers" not in SEC_CACHE:
        SEC_CACHE["tickers"] = fetch_json(
            "https://www.sec.gov/files/company_tickers.json", user_agent
        )
    return {
        str(record["ticker"]).upper(): str(record["cik_str"]).zfill(10)
        for record in SEC_CACHE["tickers"].values()
    }


def latest_shares_outstanding(cik: str, user_agent: str) -> float | None:
    facts = fetch_json(f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik}.json", user_agent)
    dei = facts.get("facts", {}).get("dei", {})
    candidates = (
        "EntityCommonStockSharesOutstanding",
        "EntityCommonStockSharesIssued",
    )
    for tag in candidates:
        units = dei.get(tag, {}).get("units", {})
        values = [
            entry
            for unit_values in units.values()
            for entry in unit_values
            if isinstance(entry.get("val"), (int, float))
        ]
        if values:
            return float(
                max(
                    values,
                    key=lambda entry: (entry.get("filed", ""), entry.get("end", "")),
                )["val"]
            )
    return None


def market_history(ticker: str) -> list[dict[str, float | str]]:
    request = Request(
        f"{YAHOO_CHART_BASE}/{quote(ticker)}?range=6mo&interval=1d",
        headers={"User-Agent": "Mozilla/5.0 InstitutionalInvestmentPredictor/1.0"},
    )
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError) as error:
        logger.exception("Yahoo Finance daily history request failed for %s", ticker)
        raise HTTPException(
            status_code=502,
            detail=f"Yahoo Finance daily history request failed: {error}",
        ) from error
    except json.JSONDecodeError as error:
        logger.exception("Yahoo Finance returned invalid JSON for %s", ticker)
        raise HTTPException(
            status_code=502,
            detail=f"No usable daily price history was returned for {ticker}.",
        ) from error
    chart = payload.get("chart", {})
    chart_error = chart.get("error")
    if chart_error:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Yahoo Finance has no daily history for {ticker}: "
                f"{chart_error.get('description', 'unknown ticker')}"
            ),
        )
    chart_results = chart.get("result") or []
    if not chart_results:
        raise HTTPException(
            status_code=404,
            detail=f"No usable daily price history was returned for {ticker}.",
        )
    result = chart_results[0]
    timestamps = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_data.get("close") or []
    volumes = quote_data.get("volume") or []
    results: list[dict[str, float | str]] = []
    for index, timestamp in enumerate(timestamps):
        if index >= len(closes) or index >= len(volumes):
            continue
        close = closes[index]
        volume = volumes[index]
        if close is None or volume is None:
            continue
        results.append(
            {
                "date": datetime.fromtimestamp(timestamp, UTC).date().isoformat(),
                "close": float(close),
                "volume": float(volume),
            }
        )
    if not results:
        raise HTTPException(
            status_code=404, detail=f"No price history found for {ticker}."
        )
    return results


def volume_anomaly(history: list[dict[str, float | str]]) -> dict[str, Any]:
    if len(history) < 35:
        return {
            "status": "insufficient_history",
            "baseline_sessions": max(len(history) - 5, 0),
            "baseline_average_volume": None,
            "latest_volume": float(history[-1]["volume"]) if history else None,
            "latest_volume_ratio": None,
            "latest_z_score": None,
            "sustained_anomaly_days": 0,
            "watchlist_candidate": False,
        }
    baseline = [float(row["volume"]) for row in history[-35:-5]]
    latest_five = history[-5:]
    baseline_average = statistics.fmean(baseline)
    latest_volume = float(latest_five[-1]["volume"])
    ratio = latest_volume / baseline_average if baseline_average > 0 else None
    deviation = statistics.pstdev(baseline)
    z_score = (latest_volume - baseline_average) / deviation if deviation > 0 else None
    sustained_days = 0
    if baseline_average > 0:
        for row in reversed(latest_five):
            if float(row["volume"]) < baseline_average * 1.5:
                break
            sustained_days += 1
    candidate = ratio is not None and ratio >= 1.5 and sustained_days >= 3
    return {
        "status": "watchlist_candidate" if candidate else "no_sustained_anomaly",
        "baseline_sessions": 30,
        "baseline_average_volume": round(baseline_average, 2),
        "latest_volume": latest_volume,
        "latest_volume_ratio": round(ratio, 4) if ratio is not None else None,
        "latest_z_score": round(z_score, 4) if z_score is not None else None,
        "sustained_anomaly_days": sustained_days,
        "watchlist_candidate": candidate,
        "threshold_volume_ratio": 1.5,
        "note": (
            "Heuristic volume screen only; no catalyst, institutional trade, or "
            "sentiment confirmation is available."
        ),
    }


def position_changes() -> list[dict[str, Any]]:
    with closing(database()) as connection:
        managers = connection.execute(
            "SELECT cik, name FROM managers ORDER BY name"
        ).fetchall()
        output: list[dict[str, Any]] = []
        for manager in managers:
            filings = connection.execute(
                """
                SELECT accession, report_date, filed_at, primary_document FROM filings
                WHERE manager_cik = ? ORDER BY report_date DESC, filed_at DESC LIMIT 2
                """,
                (manager["cik"],),
            ).fetchall()
            if not filings:
                continue
            if len(filings) < 2:
                continue
            current = connection.execute(
                "SELECT * FROM holdings WHERE accession = ?", (filings[0]["accession"],)
            ).fetchall()
            previous: dict[tuple[str, str, str | None], sqlite3.Row] = {}
            if len(filings) > 1:
                previous = {
                    (item["cusip"], item["title_of_class"], item["put_call"]): item
                    for item in connection.execute(
                        "SELECT * FROM holdings WHERE accession = ?",
                        (filings[1]["accession"],),
                    ).fetchall()
                }
            current_keys: set[tuple[str, str, str | None]] = set()
            for holding in current:
                key = (holding["cusip"], holding["title_of_class"], holding["put_call"])
                current_keys.add(key)
                old = previous.get(key)
                old_shares = old["shares"] if old else 0
                delta_shares = holding["shares"] - old_shares
                if old is None:
                    change = "new"
                elif delta_shares > 0:
                    change = "increased"
                elif delta_shares < 0:
                    change = "reduced"
                else:
                    change = "unchanged"
                if change != "unchanged":
                    output.append(
                        {
                            "manager": manager["name"],
                            "manager_cik": manager["cik"],
                            "issuer": holding["issuer"],
                            "cusip": holding["cusip"],
                            "title_of_class": holding["title_of_class"],
                            "change": change,
                            "shares": holding["shares"],
                            "previous_shares": old_shares,
                            "share_change": delta_shares,
                            "reported_value_usd": holding["value_thousands"] * 1000,
                            "report_date": filings[0]["report_date"],
                            "filed_at": filings[0]["filed_at"],
                            "previous_report_date": filings[1]["report_date"]
                            if len(filings) > 1
                            else None,
                            "source_url": sec_filing_url(
                                manager["cik"],
                                filings[0]["accession"],
                                filings[0]["primary_document"],
                            ),
                        }
                    )
            for key, old in previous.items():
                if key not in current_keys:
                    output.append(
                        {
                            "manager": manager["name"],
                            "manager_cik": manager["cik"],
                            "issuer": old["issuer"],
                            "cusip": old["cusip"],
                            "title_of_class": old["title_of_class"],
                            "change": "closed_or_not_reported",
                            "shares": 0,
                            "previous_shares": old["shares"],
                            "share_change": -old["shares"],
                            "reported_value_usd": 0,
                            "report_date": filings[0]["report_date"],
                            "filed_at": filings[0]["filed_at"],
                            "previous_report_date": filings[1]["report_date"],
                            "source_url": sec_filing_url(
                                manager["cik"],
                                filings[0]["accession"],
                                filings[0]["primary_document"],
                            ),
                        }
                    )
        output.sort(
            key=lambda row: (row["report_date"], abs(row["share_change"])), reverse=True
        )
        return output


app = FastAPI(
    title="Portfolio Risk Analyzer",
    description=(
        "Privacy-conscious deterministic analysis of user-supplied portfolio holdings, "
        "mutual-fund overlap, and INR-denominated stress scenarios."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "portfolio-risk-analyzer"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    try:
        return analyze_portfolio(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/status")
def status() -> dict[str, Any]:
    with closing(database()) as connection:
        manager_count = connection.execute("SELECT COUNT(*) FROM managers").fetchone()[
            0
        ]
        filing_count = connection.execute("SELECT COUNT(*) FROM filings").fetchone()[0]
    return {
        "service": "Institutional Investment Predictor",
        "sec_configured": bool(get_sec_user_agent() and "@" in get_sec_user_agent()),
        "market_data_provider": "Yahoo Finance public daily chart (unofficial)",
        "database": "SQLite",
        "manager_count": manager_count,
        "filing_count": filing_count,
        "prediction_note": (
            "13F data is disclosed after the reporting period; changes are historical, "
            "not pre-disclosure predictions."
        ),
    }


@app.get("/api/v1/managers")
def list_managers() -> dict[str, Any]:
    with closing(database()) as connection:
        managers = connection.execute(
            """
            SELECT m.cik, m.name, m.added_at,
                (SELECT COUNT(*) FROM filings f WHERE f.manager_cik=m.cik) AS filing_count,
                (SELECT MAX(report_date) FROM filings f WHERE f.manager_cik=m.cik) AS latest_report_date
            FROM managers m ORDER BY m.name
            """
        ).fetchall()
    return {"managers": [dict(manager) for manager in managers]}


@app.post("/api/v1/managers", status_code=201)
def add_manager(body: ManagerCreate) -> dict[str, Any]:
    with closing(database()) as connection:
        try:
            connection.execute(
                "INSERT INTO managers (cik, name, added_at) VALUES (?, ?, ?)",
                (body.cik, body.name, datetime.now(UTC).isoformat()),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409, detail="That CIK is already being tracked."
            ) from error
    return {"cik": body.cik, "name": body.name, "filing_count": 0}


@app.delete("/api/v1/managers/{cik}", status_code=204)
def delete_manager(cik: str) -> None:
    if not CIK_PATTERN.fullmatch(cik):
        raise HTTPException(status_code=422, detail="CIK must contain digits only.")
    with closing(database()) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        result = connection.execute(
            "DELETE FROM managers WHERE cik = ?", (cik.zfill(10),)
        )
        connection.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tracked manager not found.")


@app.post("/api/v1/refresh")
def refresh_filings() -> dict[str, Any]:
    user_agent = require_sec_user_agent()
    managers = list_managers()["managers"]
    results = []
    for manager in managers:
        try:
            results.append(
                {"status": "updated", **refresh_manager(manager["cik"], user_agent)}
            )
        except HTTPException as error:
            logger.exception("Refresh failed for manager CIK %s", manager["cik"])
            results.append(
                {
                    "status": "error",
                    "cik": manager["cik"],
                    "manager": manager["name"],
                    "error": error.detail,
                }
            )
    return {
        "refreshed_at": datetime.now(UTC).isoformat(),
        "results": results,
        "changes": position_changes(),
    }


@app.get("/api/v1/holdings")
def holdings(manager_cik: str | None = None) -> dict[str, Any]:
    query = """
        SELECT m.name AS manager, m.cik AS manager_cik, f.form, f.report_date,
            f.filed_at, h.issuer, h.cusip, h.title_of_class, h.value_thousands * 1000
            AS reported_value_usd, h.shares, h.share_type, h.put_call
        FROM holdings h JOIN filings f ON f.accession=h.accession
        JOIN managers m ON m.cik=f.manager_cik
    """
    params: tuple[str, ...] = ()
    if manager_cik:
        if not CIK_PATTERN.fullmatch(manager_cik):
            raise HTTPException(status_code=422, detail="CIK must contain digits only.")
        query += " WHERE m.cik = ?"
        params = (manager_cik.zfill(10),)
    query += " ORDER BY f.report_date DESC, h.value_thousands DESC LIMIT 5000"
    with closing(database()) as connection:
        rows = connection.execute(query, params).fetchall()
    return {"holdings": [dict(row) for row in rows], "count": len(rows)}


@app.get("/api/v1/signals")
def signals() -> dict[str, Any]:
    changes = position_changes()
    return {
        "signals": changes,
        "count": len(changes),
        "interpretation": "Reported quarter-over-quarter holdings changes; not pre-disclosure predictions.",
    }


@app.get("/api/v1/dashboard")
def dashboard() -> dict[str, Any]:
    with closing(database()) as connection:
        manager_count = connection.execute("SELECT COUNT(*) FROM managers").fetchone()[
            0
        ]
        filing_count = connection.execute("SELECT COUNT(*) FROM filings").fetchone()[0]
        holding_count = connection.execute(
            """
            WITH latest AS (
                SELECT accession,
                    ROW_NUMBER() OVER (
                        PARTITION BY manager_cik
                        ORDER BY report_date DESC, filed_at DESC
                    ) AS rank
                FROM filings
            )
            SELECT COUNT(*) FROM holdings h
            JOIN latest l ON l.accession = h.accession
            WHERE l.rank = 1
            """
        ).fetchone()[0]
        latest_filing = connection.execute(
            "SELECT MAX(filed_at) AS filed_at, MAX(report_date) AS report_date FROM filings"
        ).fetchone()
    changes = position_changes()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manager_count": manager_count,
        "filing_count": filing_count,
        "holding_count": holding_count,
        "changed_positions": len(changes),
        "latest_filing_date": latest_filing["filed_at"],
        "latest_report_date": latest_filing["report_date"],
        "recent_changes": changes[:10],
        "prediction_note": (
            "13F disclosures arrive up to 45 days after quarter-end and are backward-looking. "
            "No trained probability of future purchases is produced."
        ),
    }


@app.post("/api/v1/screen")
def screen_market(request: MarketScreenRequest) -> dict[str, Any]:
    history = market_history(request.ticker)
    recent_30 = history[-30:]
    recent_90 = history[-90:]
    recent_5 = history[-5:]
    adtv_30 = (
        sum(row["close"] * row["volume"] for row in recent_30) / 30
        if len(recent_30) == 30
        else None
    )
    adtv_90 = (
        sum(row["close"] * row["volume"] for row in recent_90) / 90
        if len(recent_90) == 90
        else None
    )
    five_day_dollar_volume = sum(row["close"] * row["volume"] for row in recent_5)
    target_position = request.fund_size * request.target_position_percent / 100
    impact_fraction = target_position / max(five_day_dollar_volume, 1)
    user_agent = get_sec_user_agent()
    market_cap: float | None = None
    shares_outstanding: float | None = None
    if user_agent and "@" in user_agent:
        ticker_directory = get_ticker_directory(user_agent)
        cik = ticker_directory.get(request.ticker)
        if cik:
            shares_outstanding = latest_shares_outstanding(cik, user_agent)
            if shares_outstanding is not None:
                market_cap = history[-1]["close"] * shares_outstanding
    market_cap_pass = (
        market_cap is not None and market_cap >= request.minimum_market_cap
    )
    adtv_pass = adtv_30 is not None and adtv_30 >= request.minimum_adtv
    size_pass = impact_fraction <= request.maximum_five_day_volume_fraction
    anomaly = volume_anomaly(history)
    checks = {
        "market_cap": "pass"
        if market_cap_pass
        else ("fail" if market_cap is not None else "unavailable"),
        "adtv_30d": "pass"
        if adtv_pass
        else ("unavailable" if adtv_30 is None else "fail"),
        "position_size_vs_5d_dollar_volume": "pass" if size_pass else "fail",
    }
    if any(value == "fail" for value in checks.values()):
        result_status = "Fails screen"
    elif any(value == "unavailable" for value in checks.values()):
        result_status = "Incomplete"
    else:
        result_status = "Investable"
    sources = ["Yahoo Finance public daily chart"]
    warning = "Daily end-of-day data only; not real-time trade or dark-pool data."
    if user_agent and "@" in user_agent:
        sources.extend(["SEC company_tickers.json", "SEC companyfacts"])
    else:
        warning += " SEC company-facts market-cap enrichment is unavailable until SEC access is configured."
    return {
        "ticker": request.ticker,
        "price_date": history[-1]["date"],
        "latest_close": history[-1]["close"],
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "adtv_30d": round(adtv_30, 2) if adtv_30 is not None else None,
        "adtv_90d": round(adtv_90, 2) if adtv_90 is not None else None,
        "history_session_count": len(history),
        "five_day_dollar_volume": round(five_day_dollar_volume, 2),
        "fund_size": request.fund_size,
        "target_position": round(target_position, 2),
        "position_vs_five_day_volume": round(impact_fraction, 6),
        "maximum_allowed_fraction": request.maximum_five_day_volume_fraction,
        "volume_anomaly": anomaly,
        "status": result_status,
        "checks": checks,
        "sources": sources,
        "warning": warning,
    }
