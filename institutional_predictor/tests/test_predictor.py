from fastapi.testclient import TestClient

from institutional_predictor import app as predictor


def create_test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "DATABASE_PATH", tmp_path / "test.sqlite3")
    return TestClient(predictor.app)


def test_manager_lifecycle_and_status(tmp_path, monkeypatch):
    client = create_test_client(tmp_path, monkeypatch)
    created = client.post(
        "/api/v1/managers",
        json={"name": "Example Investment Adviser", "cik": "12345"},
    )
    assert created.status_code == 201
    assert created.json()["cik"] == "0000012345"
    assert (
        client.get("/api/v1/managers").json()["managers"][0]["name"]
        == "Example Investment Adviser"
    )
    assert (
        client.post(
            "/api/v1/managers",
            json={"name": "Duplicate", "cik": "12345"},
        ).status_code
        == 409
    )
    assert client.delete("/api/v1/managers/0000012345").status_code == 204
    assert client.get("/api/v1/status").json()["manager_count"] == 0


def test_filing_rows_choose_latest_filing_for_each_report_period():
    submissions = {
        "filings": {
            "recent": {
                "form": ["13F-HR", "13F-HR/A", "4"],
                "filingDate": ["2026-05-10", "2026-05-20", "2026-04-10"],
                "reportDate": ["2026-03-31", "2026-03-31", "2026-04-01"],
                "accessionNumber": ["a-1", "a-2", "a-3"],
                "primaryDocument": ["a.xml", "b.xml", "c.xml"],
            }
        }
    }
    rows = predictor.filing_rows(submissions)
    assert len(rows) == 1
    assert rows[0]["accession"] == "a-2"


def test_refresh_requires_a_real_sec_contact(tmp_path, monkeypatch):
    client = create_test_client(tmp_path, monkeypatch)
    monkeypatch.setattr(predictor, "get_sec_user_agent", lambda: "")
    response = client.post("/api/v1/refresh")
    assert response.status_code == 503
    assert "monitored contact email" in response.json()["detail"]


def test_sec_information_table_parsing(tmp_path, monkeypatch):
    xml = """<?xml version="1.0"?>
    <informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
      <infoTable><nameOfIssuer>Example Corp</nameOfIssuer><titleOfClass>COM</titleOfClass>
        <cusip>123456789</cusip><value>500</value>
        <shrsOrPrnAmt><sshPrnamt>2500</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
      </infoTable>
    </informationTable>"""
    monkeypatch.setattr(predictor, "DATABASE_PATH", tmp_path / "unused.sqlite3")
    monkeypatch.setattr(
        predictor,
        "fetch_json",
        lambda url, user_agent: {
            "directory": {
                "item": [{"name": "form13fInfoTable.xml"}],
            }
        },
    )
    monkeypatch.setattr(predictor, "fetch_text", lambda *args, **kwargs: xml)

    result = predictor.extract_information_table(
        "0000000001", "0001-02-03", "primary.htm", "Agent contact@example.org"
    )
    assert result == [
        {
            "cusip": "123456789",
            "issuer": "Example Corp",
            "title_of_class": "COM",
            "value_thousands": 500.0,
            "shares": 2500.0,
            "share_type": "SH",
            "put_call": None,
        }
    ]


def test_quarterly_changes_compare_distinct_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "DATABASE_PATH", tmp_path / "changes.sqlite3")
    with predictor.database() as connection:
        connection.execute(
            "INSERT INTO managers (cik, name, added_at) VALUES (?, ?, ?)",
            ("0000000001", "Example Manager", "2026-01-01T00:00:00+00:00"),
        )
        connection.executemany(
            """
            INSERT INTO filings
            (accession, manager_cik, form, filed_at, report_date, primary_document)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("old", "0000000001", "13F-HR", "2026-02-10", "2025-12-31", "old.xml"),
                ("new", "0000000001", "13F-HR", "2026-05-10", "2026-03-31", "new.xml"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO holdings
            (accession, cusip, issuer, title_of_class, value_thousands,
             shares, share_type, put_call)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("old", "123456789", "Example Corp", "COM", 100, 1000, "SH", None),
                ("new", "123456789", "Example Corp", "COM", 150, 1500, "SH", None),
                ("new", "987654321", "New Corp", "COM", 75, 500, "SH", None),
            ],
        )
        connection.commit()

    changes = predictor.position_changes()
    assert sorted(
        (item["issuer"], item["change"], item["share_change"]) for item in changes
    ) == [
        ("Example Corp", "increased", 500.0),
        ("New Corp", "new", 500.0),
    ]


def test_volume_anomaly_requires_three_consecutive_high_volume_sessions():
    baseline = [
        {"date": str(index), "close": 100.0, "volume": 100.0} for index in range(30)
    ]
    sustained = baseline + [
        {"date": str(index), "close": 100.0, "volume": volume}
        for index, volume in enumerate((100.0, 100.0, 160.0, 160.0, 160.0))
    ]
    isolated = baseline + [
        {"date": str(index), "close": 100.0, "volume": volume}
        for index, volume in enumerate((100.0, 100.0, 100.0, 100.0, 200.0))
    ]

    assert predictor.volume_anomaly(sustained)["watchlist_candidate"] is True
    assert predictor.volume_anomaly(sustained)["sustained_anomaly_days"] == 3
    assert predictor.volume_anomaly(isolated)["watchlist_candidate"] is False
    assert predictor.volume_anomaly(isolated)["sustained_anomaly_days"] == 1


def test_liquidity_screen_uses_market_history_and_sec_share_count(monkeypatch):
    monkeypatch.setattr(
        predictor,
        "market_history",
        lambda ticker: [
            {
                "date": f"2026-07-{(index % 28) + 1:02d}",
                "close": 100.0,
                "volume": 1_000_000.0,
            }
            for index in range(90)
        ],
    )
    monkeypatch.setattr(
        predictor, "get_sec_user_agent", lambda: "IIP contact@example.org"
    )
    monkeypatch.setattr(
        predictor, "get_ticker_directory", lambda user_agent: {"ABC": "0000000001"}
    )
    monkeypatch.setattr(
        predictor, "latest_shares_outstanding", lambda cik, user_agent: 2_000_000_000
    )

    result = predictor.screen_market(
        predictor.MarketScreenRequest(ticker="abc", fund_size=100_000_000)
    )
    assert result["market_cap"] == 200_000_000_000
    assert result["adtv_30d"] == 100_000_000
    assert result["adtv_90d"] == 100_000_000
    assert result["status"] == "Investable"
    assert result["checks"]["position_size_vs_5d_dollar_volume"] == "pass"


def test_liquidity_screen_does_not_claim_full_windows_from_partial_history(monkeypatch):
    monkeypatch.setattr(
        predictor,
        "market_history",
        lambda ticker: [{"date": "2026-10-22", "close": 100.0, "volume": 1_000_000.0}],
    )
    monkeypatch.setattr(predictor, "get_sec_user_agent", lambda: "")

    result = predictor.screen_market(
        predictor.MarketScreenRequest(ticker="abc", fund_size=100_000_000)
    )
    assert result["adtv_30d"] is None
    assert result["adtv_90d"] is None
    assert result["checks"]["adtv_30d"] == "unavailable"
    assert result["status"] == "Incomplete"
    assert result["checks"]["market_cap"] == "unavailable"
