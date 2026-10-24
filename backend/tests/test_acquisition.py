"""Checks for the acquisition adapters without making network requests."""

import csv
import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pytest


def acquisition_scripts():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts import download_absl_portfolios, download_nse_bhavcopy

    return download_absl_portfolios, download_nse_bhavcopy


absl, nse = acquisition_scripts()


def zipped_csv(filename: str, content: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(filename, content)
    return output.getvalue()


def test_default_universe_includes_both_supplied_months():
    folder = nse.project_root() / "data" / "absl_flexi_cap" / "normalized"
    universe = nse.load_universe(sorted(folder.glob("*.csv")))
    assert len(universe) == 86
    assert universe["INE059A01026"]["company"] == "Cipla Ltd."
    assert universe["INE044A01036"]["company"] == "Sun Pharmaceutical Industries Ltd."


def test_nse_zero_volume_and_exact_daily_source_are_importable(tmp_path, monkeypatch):
    source_url = nse.archive_url(date(2026, 10, 8))
    data = zipped_csv(
        "bhavcopy.csv",
        "TradDt,ISIN,TckrSymb,SctySrs,ClsPric,TtlTradgVol\n"
        "2026-10-08,INE059A01026,CIPLA,EQ,1250.50,0\n"
        "2026-10-07,INE044A01036,SUNPHARMA,EQ,100,300\n",
    )
    universe = {
        "INE059A01026": {"company": "Cipla Ltd.", "sector": "", "industry": "Pharmaceuticals"},
        "INE044A01036": {"company": "Sun Pharmaceutical Industries Ltd."},
    }
    records = nse.parse_archive(data, date(2026, 10, 8), universe, source_url)
    assert len(records) == 1
    assert records[0]["volume"] == "0"
    assert records[0]["source_url"] == source_url

    target = tmp_path / "prices.csv"
    assert nse.write_month(target, records) == 1
    assert nse.write_month(target, records) == 1
    with target.open(newline="", encoding="utf-8") as stream:
        assert list(csv.DictReader(stream)) == records

    monkeypatch.setenv("RISKORA_DB", str(tmp_path / "riskora.sqlite3"))
    monkeypatch.setenv("RISKORA_UPLOAD_DIR", str(tmp_path / "uploads"))
    from app.db import connect, init_db
    from app.ingestion import import_market

    init_db()
    import_market(target.read_bytes(), source_url=nse.LANDING)
    with connect() as db:
        stored = db.execute("SELECT volume,source_url FROM market_observations").fetchone()
    assert stored["volume"] == 0
    assert stored["source_url"] == source_url


def test_portfolio_zip_rejects_parent_directory(tmp_path):
    data = zipped_csv("../escape.csv", "unsafe")
    with pytest.raises(ValueError, match="Unsafe portfolio ZIP entry"):
        absl.safe_extract_zip(data, tmp_path / "extracted")
    assert not (tmp_path / "escape.csv").exists()


def test_portfolio_manifest_dry_run_uses_two_selected_urls(capsys):
    assert absl.download(["--from-month", "2026-08", "--to-month", "2026-09", "--dry-run"]) == []
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("2026-08-31 https://")
    assert lines[1].startswith("2026-09-30 https://")
