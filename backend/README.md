# Riskora API

Canonical backend: `app.main:app`. From this directory, install `requirements.txt`, set `RISKORA_ADMIN_TOKEN`, and run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.

See the [root README](../README.md) for the CSV schemas, data sources, model method, API contract, security settings, and demonstration steps. Interactive endpoint documentation: <http://127.0.0.1:8001/docs>.

Run tests from this directory with `python -m pytest -q`.
