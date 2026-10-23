"""Deterministic synthetic data for UI and pipeline testing only."""

from __future__ import annotations

import calendar
import csv
import io
from datetime import date, timedelta

from .db import connect
from .ingestion import import_holdings, import_market


def csv_bytes(records, fields):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def load_synthetic_demo():
    with connect() as db:
        existing = db.execute(
            "SELECT COUNT(*) FROM snapshots WHERE source_kind='synthetic'"
        ).fetchone()[0]
    if existing:
        return {"status": "already_loaded", "snapshots": existing, "source_kind": "synthetic"}
    securities = [
        {
            "isin": f"IN{i:010d}",
            "company": f"Synthetic Company {i:02d}",
            "ticker": f"SYN{i:02d}",
            "sector": ("Banking", "Technology", "Industrials")[i % 3],
            "industry": ("Banks", "Software", "Manufacturing")[i % 3],
        }
        for i in range(1, 13)
    ]
    market = []
    day = date(2024, 1, 1)
    while day <= date(2025, 4, 10):
        if day.weekday() < 5:
            for i, security in enumerate(securities):
                price = round(
                    100
                    + i * 12
                    + (day - date(2024, 1, 1)).days * (0.03 + i * 0.002)
                    + ((day.day * (i + 3)) % 17) * 0.3,
                    2,
                )
                market.append(
                    {
                        **security,
                        "date": day.isoformat(),
                        "close": price,
                        "adjusted_close": price,
                        "volume": 100000 + i * 5000 + day.day * 100,
                    }
                )
        day += timedelta(days=1)
    import_market(
        csv_bytes(market, list(market[0])),
        source_url="sample://synthetic-market",
        source_kind="synthetic",
    )
    count = 0
    for month_index in range(15):
        year = 2024 + month_index // 12
        month = month_index % 12 + 1
        report = date(year, month, calendar.monthrange(year, month)[1])
        published = report + timedelta(days=8)
        for fund_number in range(2):
            # The five constituents rotate, creating new additions and exits.
            chosen = [
                securities[(month_index + fund_number * 3 + offset) % len(securities)]
                for offset in range(5)
            ]
            records = [
                {**security, "weight": 20, "units": 1000 + month_index * 10 + fund_number}
                for security in chosen
            ]
            import_holdings(
                csv_bytes(records, list(records[0])),
                scheme_id=f"synthetic_fund_{fund_number + 1}",
                scheme_name=f"Synthetic Research Fund {fund_number + 1}",
                amc="Synthetic AMC",
                category="Synthetic equity",
                report_date=report.isoformat(),
                published_at=published.isoformat(),
                source_url=f"sample://synthetic-{month_index}-{fund_number}",
                complete=True,
                source_kind="synthetic",
            )
            count += 1
    return {
        "status": "loaded",
        "snapshots": count,
        "market_rows": len(market),
        "source_kind": "synthetic",
        "warning": "Entirely synthetic data for UI and pipeline testing; no real-world performance claim.",
    }
