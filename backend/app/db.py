"""SQLite storage for the mutual fund research application."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "riskora.sqlite3"


def db_path() -> Path:
    return Path(os.getenv("RISKORA_DB", str(DEFAULT_DB))).resolve()


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS schemes (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, amc TEXT NOT NULL, category TEXT,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('official','user_import','synthetic'))
);
CREATE TABLE IF NOT EXISTS securities (
 isin TEXT PRIMARY KEY, company TEXT NOT NULL, ticker TEXT, sector TEXT, industry TEXT
);
CREATE TABLE IF NOT EXISTS identifier_mappings (
 isin TEXT NOT NULL REFERENCES securities(isin), ticker TEXT NOT NULL, source_url TEXT,
 reviewed_at TEXT, PRIMARY KEY(isin,ticker)
);
CREATE TABLE IF NOT EXISTS snapshots (
 id INTEGER PRIMARY KEY, scheme_id TEXT NOT NULL REFERENCES schemes(id),
 report_date TEXT NOT NULL, published_at TEXT NOT NULL, retrieved_at TEXT NOT NULL,
 source_url TEXT NOT NULL, file_sha256 TEXT NOT NULL, source_kind TEXT NOT NULL,
 complete INTEGER NOT NULL CHECK(complete IN (0,1)), weight_total REAL NOT NULL,
 parse_status TEXT NOT NULL, warnings TEXT NOT NULL DEFAULT '[]',
 UNIQUE(scheme_id,report_date)
);
CREATE TABLE IF NOT EXISTS holdings (
 snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
 isin TEXT NOT NULL REFERENCES securities(isin), weight REAL NOT NULL,
 units REAL, market_value REAL, PRIMARY KEY(snapshot_id,isin)
);
CREATE TABLE IF NOT EXISTS market_observations (
 isin TEXT NOT NULL REFERENCES securities(isin), date TEXT NOT NULL,
 close REAL NOT NULL, volume REAL NOT NULL, adjusted_close REAL,
 source_url TEXT NOT NULL, imported_at TEXT NOT NULL,
 source_kind TEXT NOT NULL DEFAULT 'user_import', PRIMARY KEY(isin,date,source_kind)
);
CREATE TABLE IF NOT EXISTS company_events (
 id INTEGER PRIMARY KEY, isin TEXT NOT NULL REFERENCES securities(isin),
 title TEXT NOT NULL, category TEXT NOT NULL, published_at TEXT NOT NULL,
 source_url TEXT NOT NULL, excerpt TEXT NOT NULL, imported_at TEXT NOT NULL,
 source_kind TEXT NOT NULL, UNIQUE(isin,published_at,source_url)
);
CREATE TABLE IF NOT EXISTS extracted_events (
 event_id INTEGER PRIMARY KEY REFERENCES company_events(id),
 status TEXT NOT NULL, model TEXT, extracted_json TEXT, processed_at TEXT,
 error TEXT
);
CREATE TABLE IF NOT EXISTS labels (
 scheme_id TEXT NOT NULL, isin TEXT NOT NULL, cutoff TEXT NOT NULL,
 target_report_date TEXT NOT NULL, horizon TEXT NOT NULL, label TEXT NOT NULL,
 previous_snapshot_id INTEGER NOT NULL, next_snapshot_id INTEGER NOT NULL,
 materiality REAL NOT NULL,
 PRIMARY KEY(scheme_id,isin,cutoff,horizon)
);
CREATE TABLE IF NOT EXISTS feature_records (
 scheme_id TEXT NOT NULL, isin TEXT NOT NULL, cutoff TEXT NOT NULL,
 horizon TEXT NOT NULL, feature_version TEXT NOT NULL, values_json TEXT NOT NULL,
 PRIMARY KEY(scheme_id,isin,cutoff,horizon,feature_version)
);
CREATE TABLE IF NOT EXISTS training_runs (
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL, source_kind TEXT, horizon TEXT NOT NULL DEFAULT 'month',
 model_version TEXT, feature_version TEXT,
 train_end TEXT, test_start TEXT, test_end TEXT, metrics_json TEXT,
 artifact_path TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS evaluation_results (
 run_id INTEGER NOT NULL REFERENCES training_runs(id), phase TEXT NOT NULL,
 period TEXT NOT NULL, model TEXT NOT NULL, metrics_json TEXT NOT NULL,
 PRIMARY KEY(run_id,phase,period,model)
);
CREATE TABLE IF NOT EXISTS predictions (
 id INTEGER PRIMARY KEY, run_id INTEGER REFERENCES training_runs(id),
 scheme_id TEXT NOT NULL, isin TEXT NOT NULL, horizon TEXT NOT NULL,
 cutoff TEXT NOT NULL, score REAL NOT NULL, created_at TEXT NOT NULL,
 features_json TEXT NOT NULL, evidence_json TEXT NOT NULL,
 UNIQUE(run_id,scheme_id,isin,horizon,cutoff)
);
"""


def init_db():
    with connect() as db:
        db.executescript(SCHEMA)
        columns = {row[1] for row in db.execute("PRAGMA table_info(market_observations)")}
        if "source_kind" not in columns:
            db.execute(
                "ALTER TABLE market_observations ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'user_import'"
            )
        market_pk = [
            row[1] for row in db.execute("PRAGMA table_info(market_observations)") if row[5]
        ]
        if market_pk != ["isin", "date", "source_kind"]:
            db.executescript("""
                CREATE TABLE market_observations_migrated (
                    isin TEXT NOT NULL REFERENCES securities(isin), date TEXT NOT NULL,
                    close REAL NOT NULL, volume REAL NOT NULL, adjusted_close REAL,
                    source_url TEXT NOT NULL, imported_at TEXT NOT NULL,
                    source_kind TEXT NOT NULL DEFAULT 'user_import',
                    PRIMARY KEY(isin,date,source_kind)
                );
                INSERT INTO market_observations_migrated
                    SELECT isin,date,close,volume,adjusted_close,source_url,imported_at,source_kind
                    FROM market_observations;
                DROP TABLE market_observations;
                ALTER TABLE market_observations_migrated RENAME TO market_observations;
            """)
        run_columns = {row[1] for row in db.execute("PRAGMA table_info(training_runs)")}
        if "horizon" not in run_columns:
            db.execute("ALTER TABLE training_runs ADD COLUMN horizon TEXT NOT NULL DEFAULT 'month'")


def rows(db, sql, args=()):
    return [dict(row) for row in db.execute(sql, args).fetchall()]
