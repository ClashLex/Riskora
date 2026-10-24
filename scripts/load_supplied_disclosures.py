"""Load the supplied ABSL Flexi Cap files for local, non-training exploration.

The exact public release dates of both source workbooks are unverified.
Both snapshots therefore use the date this script observes them and remain
ineligible for comparable labels until their publication dates are verified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

from normalize_absl_xls import normalize

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "absl_flexi_cap"
sys.path.insert(0, str(ROOT / "backend"))

SCHEME_ID = "absl_flexi_cap"
SCHEME_NAME = "ADITYA BIRLA SUN LIFE FLEXI CAP FUND"
SOURCE_NOTE = (
    "Normalized holdings match the AMC workbook; exact publication date remains unverified."
)
MANIFEST = DATA_DIR / "manifests" / "absl_monthly_portfolio_manifest.csv"


def _records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _matches_workbook(csv_rows: list[dict], workbook_rows: list[dict]) -> bool:
    by_isin = {row["isin"]: row for row in csv_rows}
    if len(by_isin) != len(csv_rows) or set(by_isin) != {row["isin"] for row in workbook_rows}:
        return False
    for source in workbook_rows:
        normalized = by_isin[source["isin"]]
        if any(
            normalized[field] != source[field]
            for field in ("company", "industry", "sector", "ticker")
        ):
            return False
        if any(
            not math.isclose(
                float(normalized[field]), float(source[field]), rel_tol=1e-8, abs_tol=1e-6
            )
            for field in ("weight", "units", "market_value")
        ):
            return False
    return True


def _source_urls() -> dict[str, str]:
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        return {
            row["report_date"]: row["source_url"]
            for row in csv.DictReader(stream)
            if row["report_date"] in {"2026-08-31", "2026-09-30"}
        }


def load(observed_at: str) -> list[dict]:
    from app.db import connect, init_db
    from app.ingestion import import_holdings, read_csv

    observed = date.fromisoformat(observed_at)
    if observed < date(2026, 10, 24):
        raise ValueError("These files were first confirmed in this workspace on 2026-10-24.")
    if observed > date.today():
        raise ValueError("Observed date cannot be in the future.")
    sources = _source_urls()
    if set(sources) != {"2026-08-31", "2026-09-30"}:
        raise ValueError("The acquisition manifest is missing an ABSL source URL.")
    files = (
        ("2026-08-31", "August 31, 2026", "31082026_ABSLMF_MonthlyDisclosure.xls"),
        ("2026-09-30", "September 30, 2026", "30092026_ABSLMF_MonthlyDisclosure.xls"),
    )
    for report_date, heading, workbook_name in files:
        workbook = DATA_DIR / "raw" / workbook_name
        normalized = DATA_DIR / "normalized" / f"ABSLMF_BSLEQTY_{report_date}.csv"
        extracted, summary = normalize(workbook)
        if summary["scheme"] != SCHEME_NAME or heading not in summary["report_heading"]:
            raise ValueError(f"The {report_date} workbook has the wrong scheme or date.")
        if not _matches_workbook(_records(normalized), extracted):
            raise ValueError(f"The {report_date} CSV differs from its source workbook.")

    imports = []
    init_db()
    for report_date, _, _ in files:
        path = DATA_DIR / "normalized" / f"ABSLMF_BSLEQTY_{report_date}.csv"
        data = path.read_bytes()
        read_csv(data, {"isin", "company", "weight"})
        digest = hashlib.sha256(data).hexdigest()
        with connect() as db:
            existing = db.execute(
                "SELECT file_sha256,availability_basis,source_url,warnings FROM snapshots WHERE scheme_id=? AND report_date=?",
                (SCHEME_ID, report_date),
            ).fetchone()
        if existing:
            if existing["file_sha256"] != digest or existing["availability_basis"] != "observed":
                raise ValueError(
                    f"Existing {report_date} snapshot differs; review it before loading."
                )
            if existing["source_url"] != sources[report_date]:
                old_warnings = json.loads(existing["warnings"])
                old_warnings = [
                    warning
                    for warning in old_warnings
                    if "source link is the AMC disclosure page" not in warning
                ]
                if SOURCE_NOTE not in old_warnings:
                    old_warnings.append(SOURCE_NOTE)
                with connect() as db:
                    db.execute(
                        "UPDATE snapshots SET source_url=?,warnings=? WHERE scheme_id=? AND report_date=?",
                        (sources[report_date], json.dumps(old_warnings), SCHEME_ID, report_date),
                    )
            imports.append({"report_date": report_date, "status": "already_loaded"})
            continue
        result = import_holdings(
            data,
            scheme_id=SCHEME_ID,
            scheme_name=SCHEME_NAME,
            amc="Aditya Birla Sun Life Mutual Fund",
            category="Flexi Cap",
            report_date=report_date,
            published_at=observed_at,
            source_url=sources[report_date],
            source_note=SOURCE_NOTE,
            complete=False,
            availability_basis="observed",
        )
        imports.append({"report_date": report_date, "status": "loaded", **result})
    return imports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--observed-at",
        default=date.today().isoformat(),
        help="YYYY-MM-DD; defaults to today",
    )
    args = parser.parse_args()
    for item in load(args.observed_at):
        print(item)
