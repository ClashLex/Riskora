# Risvanta

See beyond the returns: an illustrative portfolio-risk education workspace with an optional FastAPI backend.

## Run

Requires Node.js 20.19+ (or 22.12+) and npm. From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. `npm run build` creates a production bundle, `npm run preview` serves it, and `npm test` runs calculation tests.

To connect to the backend, start it from `backend/` with `python -m pip install -r requirements.txt` then `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`. Create `frontend/.env` from `.env.example` (or set `VITE_USE_MOCK_DATA=false`); restart Vite. By default `/api/v1` is proxied to port 8000 in development. On a separately hosted production deployment, set `VITE_API_BASE_URL` to the full backend URL including `/api/v1` and configure backend `CORS_ORIGINS` accordingly. Use `VITE_USE_MOCK_DATA=true` to return to the offline demo; switching modes does not transfer holdings.

## What you can explore

- `/` — overview, allocation, risk highlights, session-only simulation history
- `/portfolio` — add, edit, delete, search, filter, sort, export, and reset holdings; CSV import is explicitly unavailable
- `/exposure` — asset class, sector, underlying company, geography, currency, and illustrative fund look-through
- `/stress-test` — hypothetical market, sector, FX, combined, and custom scenario controls with position-level estimates
- `/insights` — deterministic findings, calculation evidence drawer, and local prototype explanations
- `/settings` — base currency, fixed FX assumptions, demo controls, privacy and disclaimer

Built with React, TypeScript, Vite, Tailwind CSS, React Router, Lucide, Recharts, React Hook Form, Zod, and Vitest. UI is dark-first with responsive layouts. The browser stores edited positions and currency preference locally; scenario history lasts only for the current page session.

## Data and calculations

The seven sample holdings, fund weights, and FX assumptions are fictional and dated 2026-01-15. `src/data.ts` defines them; `src/services/portfolio.ts` owns local persistence; `src/lib/risk.ts` provides pure conversion, allocation, look-through, and scenario functions. Converted value = holding currency value × illustrative USD-per-unit rate ÷ base currency USD-per-unit rate. Price and USD/base FX shocks combine as `(1 + asset return) × (1 + FX return) − 1`. Currency shocks affect USD-denominated holdings only when the base currency is not USD. Non-applicable positions are marked “Not modelled”. Values are estimates, not predictions or investment advice.

In API mode, holdings, converted exposure, insights, scenarios, results and template explanations come directly from backend endpoints under `/api/v1`. Backend fixtures differ from offline fixtures (and are dated 2026-06-30). The frontend uses backend valuation and source metadata, preserves incomplete results as incomplete, and does **not** recalculate API-mode results with offline constants. Backend portfolios are process-memory only and disappear on restart. Errors are shown with Retry; they never silently switch to offline data.

## Environment and future API

`.env.example` documents `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL=/api/v1`. The default without an `.env` is offline mode. API responses are validated before display, requests time out after ten seconds, and server error messages are surfaced. Never put secrets in Vite environment variables.

## Limitations

No authentication, database, live prices, verified fund holdings, AI provider, or CSV parser is included. Holdings entered by hand are not repriced or verified. API-mode portfolios have no user isolation and should only be used locally. Data and calculation evidence are illustrative. Risk outputs are hypothetical estimates, not forecasts, guarantees, or personalized advice.
