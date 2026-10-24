# Riskora API

Canonical backend: `app.main:app`. From this directory, install `requirements.txt`, set `RISKORA_ADMIN_TOKEN`, and run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.

See the [root README](../README.md) for the CSV schemas, data sources, model method, API contract, security settings, and demonstration steps. Interactive endpoint documentation: <http://127.0.0.1:8001/docs>.

Run tests from this directory with `python -m pytest -q`.

The [ABSL acquisition tools](../docs/absl-data-acquisition.md) can download portfolio archives and NSE bhavcopies into the project's ignored `data/absl_flexi_cap/downloads/` directory. Market CSVs may include a `source_url` column for the exact daily archive; `/api/v1/imports/market` stores that URL per observation and uses the form's batch URL only when the row has no URL. Downloaded files are not imported automatically.
