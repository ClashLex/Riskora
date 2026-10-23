# Risvanta backend

Risvanta is a local prototype for portfolio exposure analysis and deterministic, hypothetical risk scenarios. The API supports in-memory portfolios, multi-currency valuation, fund look-through, overlap analysis, rule-based insights, and grounded template explanations. It is a risk-education prototype, **not investment advice, a trading service, or a forecast**.

## Requirements and setup

Python 3.11 or later is required. From this `backend` directory, create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Run the API locally:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI documentation is at `http://127.0.0.1:8000/docs`; ReDoc is at `http://127.0.0.1:8000/redoc`. Liveness is available at `http://127.0.0.1:8000/health`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Environment label. |
| `DATA_MODE` | `illustrative` | Only illustrative fixture mode is implemented. Other values fail startup rather than implying live data. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated explicit origins. `*` is rejected. |
| `API_PREFIX` | `/api/v1` | Versioned API path prefix. |
| `EXPLANATION_PROVIDER` | `template` | Only deterministic template explanations are implemented. |
| `EXPLANATION_API_KEY` | unset | Reserved for future provider integration; unused and never returned. |
| `EXPLANATION_MODEL` | unset | Reserved for future provider integration; unused. |

The default build makes no external data or AI requests. Do not put credentials in fixture files.

## API routes

All request and response fields use `snake_case`. Validation and application errors use an `error` object with `code`, `message`, and `details`.

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Service liveness; does not depend on outside services. |
| `GET` | `/api/v1/portfolios` | List local portfolios and converted totals. |
| `GET` | `/api/v1/portfolios/{portfolio_id}` | Read a portfolio, holdings, valuation, and conversion warnings. |
| `POST` | `/api/v1/portfolios` | Create an empty local portfolio. |
| `POST` | `/api/v1/portfolios/{portfolio_id}/holdings` | Add a user-entered holding. |
| `PATCH` | `/api/v1/portfolios/{portfolio_id}/holdings/{holding_id}` | Update holding fields. |
| `DELETE` | `/api/v1/portfolios/{portfolio_id}/holdings/{holding_id}` | Delete a holding. |
| `POST` | `/api/v1/portfolios/{portfolio_id}/load-demo` | Reset the `demo-global` fixture. |
| `GET` | `/api/v1/portfolios/{portfolio_id}/exposure?base_currency=USD` | Asset-class, sector, company, geography, and currency exposure; fund coverage, overlap, sources, and warnings. |
| `GET` | `/api/v1/portfolios/{portfolio_id}/insights` | Deterministic concentration, overlap, currency, and data-quality insights. |
| `POST` | `/api/v1/portfolios/{portfolio_id}/scenarios/run` | Run a hypothetical market, sector, FX, combined, or custom scenario. |
| `GET` | `/api/v1/scenarios` | List the six scenario presets and limitations. |
| `POST` | `/api/v1/portfolios/{portfolio_id}/explanations` | Explain a server-calculated scenario or insight using a deterministic template. |

Example stress request:

```json
{
  "scenario_id": "combined_market_fx_shock",
  "base_currency": "USD",
  "asset_shock_percent": -10,
  "fx_shock_percent": 5
}
```

Shocks are percentage points at the API boundary and decimal returns internally. Omitted shock values use the selected preset defaults. `custom` requests can target `affected_sector`, `affected_asset_ids`, or both.

Run a scenario first, then send only its server-generated result identifier to explanations:

```json
{
  "result_id": "result-...",
  "question": "What contributed to this scenario result?"
}
```

Client-supplied calculation figures and source URLs are not accepted as explanation evidence.

## Data and calculation conventions

All included holdings, fund constituents, exchange rates, sources, and presets are synthetic local fixtures dated 2026-06-30, marked `illustrative`, and have no source URLs. They are not live prices, verified disclosures, or actual fund holdings. Data older than the 90-day prototype threshold generates a warning.

FX records define `rate` as **units of base currency for one unit of foreign currency**. Conversion is `market_value * rate`; cross rates use a deterministic shortest path through fixture pairs. A missing conversion is reported and excluded from the converted total, never replaced with 1.

Portfolio totals use top-level holdings only. Exposure and scenario calculations decompose funds into known constituents and keep uncovered value visible; constituent weights are never rescaled to 100%. Direct positions and constituent exposures are combined for overlap without adding constituents to the portfolio total. Exposure groups include source IDs, dates, statuses, and contributions.

Market and FX returns compound as `(1 + asset_return) * (1 + fx_return) - 1`. Sector shocks only affect holdings mapped to that sector. Unknown sector, currency, or hedge mappings are reported as `not_modelled`; an incomplete scenario withholds the total portfolio change while returning the modeled-row subtotal. The USD presets define a simplified USD-specific parallel shock. These deterministic simulations are not forecasts.

Concentration heuristics are documented in insight calculation details: 30%/50% for medium/high sector concentration and 40%/60% for medium/high foreign-currency exposure. They are prototype thresholds, not financial standards.

## Storage, privacy, and limitations

User-created portfolios exist only in process memory and disappear after restart. There is no authentication, authorization, ownership isolation, database, or persistence. This is for local demo use only. CORS is restricted to configured origins. No portfolio data leaves the process in template mode.

Optional AI, live market data, verified source retrieval, database persistence, authentication, and CSV ingestion are not implemented. The reserved AI environment variables do not enable a provider. Before production use, add user isolation, security controls, rate limiting, secret management, persistence safeguards, and relevant privacy and financial-services reviews.

## Tests and lint

From the `backend` directory:

```powershell
pytest -q
ruff check .
ruff format --check .
```
