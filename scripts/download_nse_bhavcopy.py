#!/usr/bin/env python3
"""Download NSE equity bhavcopies and export Riskora market CSVs for known ISINs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import re
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests

LANDING = "https://www.nseindia.com/all-reports"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RiskoraResearchDataAcquisition/1.0)",
    "Referer": LANDING,
    "Accept": "*/*",
}
FIELDS = [
    "date",
    "isin",
    "company",
    "close",
    "volume",
    "adjusted_close",
    "ticker",
    "sector",
    "industry",
    "source_url",
]
MAX_DOWNLOAD = 50 * 1024 * 1024
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "backend" / "app").is_dir():
            return parent
    raise RuntimeError("Run this script inside the Riskora project.")


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())


def parse_day(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d%b%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def archive_url(day: date) -> str:
    if day >= date(2024, 7, 8):
        return f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    month = day.strftime("%b").upper()
    return f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{day:%Y}/{month}/cm{day:%d}{month}{day:%Y}bhav.csv.zip"


def aliases(row: dict) -> dict[str, str]:
    columns = {norm(key): value for key, value in row.items()}

    def get(*keys: str) -> str:
        for key in keys:
            value = columns.get(norm(key))
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    return {
        "date": get("TradDt", "TIMESTAMP", "DATE", "BizDt"),
        "isin": get("ISIN", "ISIN NUMBER").upper(),
        "ticker": get("TckrSymb", "SYMBOL", "TICKER").upper(),
        "series": get("SctySrs", "SERIES").upper(),
        "close": get("ClsPric", "CLOSE"),
        "volume": get("TtlTradgVol", "TOTTRDQTY", "TOTAL TRADED QUANTITY", "VOLUME"),
    }


def to_float(value: str) -> float | None:
    try:
        number = float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) else None


def number_text(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".") or "0"


def load_universe(paths: list[Path]) -> dict[str, dict]:
    universe: dict[str, dict] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                isin = (row.get("isin") or "").strip().upper()
                company = (row.get("company") or "").strip()
                if not isin or not company:
                    continue
                prior = universe.get(isin)
                if prior and prior["company"].casefold() != company.casefold():
                    raise ValueError(f"Conflicting company names for {isin} across universe files.")
                universe[isin] = row
    if not universe:
        raise ValueError("No ISIN/company pairs found in the universe CSVs.")
    return universe


def extract_rows(content: bytes) -> csv.DictReader:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("NSE archive must contain exactly one CSV file.")
        info = archive.getinfo(names[0])
        if info.file_size > MAX_DOWNLOAD:
            raise ValueError("NSE CSV exceeds the 50 MB extracted size limit.")
        raw = archive.read(info)
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw.decode("cp1252")
    reader = csv.DictReader(io.StringIO(decoded))
    headers = {norm(name) for name in reader.fieldnames or []}
    if not ({"isin", "isinumber"} & headers) or not ({"clspric", "close"} & headers):
        raise ValueError("NSE archive is missing ISIN or close columns.")
    return reader


def parse_archive(
    content: bytes, requested_day: date, universe: dict[str, dict], source_url: str
) -> list[dict]:
    matched: dict[str, dict] = {}
    for row in extract_rows(content):
        item = aliases(row)
        isin = item["isin"]
        if isin not in universe or item["series"] not in {"EQ", ""}:
            continue
        if parse_day(item["date"]) != requested_day:
            continue
        close, volume = to_float(item["close"]), to_float(item["volume"])
        if close is None or close <= 0 or volume is None or volume < 0:
            continue
        source = universe[isin]
        record = {
            "date": requested_day.isoformat(),
            "isin": isin,
            "company": source["company"].strip(),
            "close": number_text(close),
            "volume": number_text(volume),
            "adjusted_close": "",
            "ticker": item["ticker"] or (source.get("ticker") or ""),
            "sector": source.get("sector") or "",
            "industry": source.get("industry") or "",
            "source_url": source_url,
        }
        if isin in matched and matched[isin] != record:
            raise ValueError(f"Conflicting NSE rows for {isin} on {requested_day}.")
        matched[isin] = record
    return list(matched.values())


def read_limited(response: requests.Response) -> bytes:
    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        size += len(chunk)
        if size > MAX_DOWNLOAD:
            raise ValueError("NSE archive exceeds the 50 MB download limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def write_month(path: Path, new_rows: list[dict]) -> int:
    combined = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"Existing market file has different columns: {path}")
            for row in reader:
                combined[(row["date"], row["isin"])] = row
    for row in new_rows:
        key = row["date"], row["isin"]
        if key in combined and combined[key] != row:
            raise ValueError(f"Existing market observation conflicts for {key}.")
        combined[key] = row
    if len(combined) > MAX_IMPORT_ROWS:
        raise ValueError(f"Market CSV would exceed {MAX_IMPORT_ROWS} rows: {path}")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(combined[key] for key in sorted(combined))
    data = output.getvalue().encode("utf-8")
    if len(data) > MAX_IMPORT_BYTES:
        raise ValueError(f"Market CSV would exceed 5 MB: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return len(combined)


def download(argv: list[str] | None = None) -> list[dict]:
    parser = argparse.ArgumentParser(description=__doc__)
    data_dir = project_root() / "data" / "absl_flexi_cap"
    parser.add_argument(
        "--universe", type=Path, action="append", help="repeat for multiple holdings CSVs"
    )
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-09-30")
    parser.add_argument("--out", type=Path, default=data_dir / "downloads" / "market_monthly")
    parser.add_argument("--raw-out", type=Path, default=data_dir / "downloads" / "nse_archives")
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if end < start or end > date.today():
        parser.error("Date range must be ordered and cannot end in the future.")
    files = args.universe or sorted((data_dir / "normalized").glob("*.csv"))
    universe = load_universe(files)
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    if args.dry_run:
        print(f"{len(universe)} ISINs from {len(files)} CSV(s); {len(days)} weekdays selected.")
        for day in days:
            print(day.isoformat(), archive_url(day))
        return []

    out = args.out.resolve()
    raw_out = args.raw_out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw_out.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list[dict]] = {}
    log: list[dict] = []
    with requests.Session() as session:
        session.headers.update(HEADERS)
        for day in days:
            url = archive_url(day)
            raw_file = raw_out / f"{day.isoformat()}.zip"
            item = {
                "date_requested": day.isoformat(),
                "url": url,
                "status": "",
                "rows_filtered": 0,
                "sha256": "",
                "detail": "",
            }
            try:
                if raw_file.exists():
                    if raw_file.stat().st_size > MAX_DOWNLOAD:
                        raise ValueError("Cached NSE archive exceeds 50 MB.")
                    content = raw_file.read_bytes()
                    item["status"] = "already_present"
                else:
                    with session.get(url, timeout=(15, 60), stream=True) as response:
                        final = urlparse(response.url)
                        if final.scheme != "https" or final.hostname not in {
                            "nsearchives.nseindia.com",
                            "www.nseindia.com",
                        }:
                            raise ValueError("NSE archive redirected to an unexpected host.")
                        if response.status_code in {403, 429}:
                            item["status"] = f"http_{response.status_code}"
                            item["detail"] = (
                                "Source restriction; stop and use the official NSE page."
                            )
                            log.append(item)
                            print(day, item["status"])
                            break
                        if response.status_code == 404:
                            item["status"] = "not_found"
                            item["detail"] = (
                                "No archive at this URL; check holiday or official report page."
                            )
                            log.append(item)
                            continue
                        response.raise_for_status()
                        content = read_limited(response)
                    item["status"] = "downloaded"
                records = parse_archive(content, day, universe, url)
                if item["status"] == "downloaded":
                    raw_file.write_bytes(content)
                item["sha256"] = hashlib.sha256(content).hexdigest()
                item["rows_filtered"] = len(records)
                if records:
                    by_month.setdefault(day.strftime("%Y-%m"), []).extend(records)
            except (requests.RequestException, OSError, ValueError, zipfile.BadZipFile) as exc:
                item["status"] = "error"
                item["detail"] = f"{type(exc).__name__}: {exc}"
            log.append(item)
            print(day, item["status"], item["rows_filtered"], item["detail"])
            if item["status"] == "downloaded":
                time.sleep(max(0.0, args.sleep))

    for month, rows in sorted(by_month.items()):
        target = out / f"nse_equity_prices_{month}.csv"
        print(target.name, write_month(target, rows), "observations")
    log_file = out / f"download_log_{start}_{end}.csv"
    with log_file.open("w", newline="", encoding="utf-8") as stream:
        fields = ["date_requested", "url", "status", "rows_filtered", "sha256", "detail"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(log)
    print("Download log:", log_file)
    print("Closes are unadjusted; check corporate actions before using returns in evaluation.")
    return log


if __name__ == "__main__":
    download()
