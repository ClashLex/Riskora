# Riskora — Indian Mutual Fund Purchase Intelligence

Riskora is a local research prototype that ranks stocks that may **newly appear in the next valid disclosed portfolio snapshot** of an Indian equity mutual-fund scheme. A disclosure reports positions at a date; it cannot reveal an order, its execution date, or a manager's intent. Scores are uncalibrated ranking scores, not probabilities or investment advice.

## Problem, users, and solution

Fund portfolio statements are retrospective. A researcher comparing Indian equity mutual-fund disclosures must assemble dated holdings, distinguish a genuinely new position from an existing one, and check what was knowable before the next statement. Riskora is intended for analysts and research teams exploring that question; it has not been validated with paying customers.

The prototype accepts normalized, attributed disclosures and optional market observations, checks comparability and publication dates, trains a point-in-time ranking model, and shows candidate stocks with their supporting inputs and a later-period evaluation. The repository contains a **synthetic model demonstration** and two supplied ABSL Flexi Cap snapshots for portfolio exploration, not an established prediction service or a verified Indian-market performance claim.

**Stack:** React 19, TypeScript, Vite, FastAPI, SQLite, scikit-learn, and an optional OpenAI-compatible language-model endpoint for grounded event extraction. See [assumptions and trade-offs](docs/event-submission/assumptions-and-tradeoffs.md) for the choices behind this scope.

For a guided explanation of the screens and data flow, see [how the site works](docs/how-the-site-works.md). For a quick, single-service public demo, see [deploy on Render](docs/DEPLOY-RENDER-SIMPLE.md). For persistent data on your own server, see [hosting Riskora live](docs/hosting-live.md).

## AIBoomi review package

| Item | Location or status |
| --- | --- |
| GitHub repository | <https://github.com/ClashLex/Riskora> (configured `origin`; local changes need publishing before reviewers see them) |
| Product demo | [Run the local prototype](#start-locally) with the [three-minute demo script](docs/event-submission/demo-runbook.md). A public app or recording URL has not been supplied. |
| Pitch deck | [Six-slide PowerPoint deck](docs/event-submission/Riskora-pitch-deck.pptx) and [editable slide content](docs/event-submission/pitch-deck.md) |
| AI impact statement | [AI impact statement](docs/event-submission/ai-impact-statement.md) (under 200 words) |
| Submission and provenance | [Handbook alignment and outstanding items](docs/event-submission/README.md) |

**Team:** Ansil Muhammed N S and Muhammed Ihsan K I. Roles and contacts have not been provided.

The event's fresh-build and surprise-element requirements depend on the actual kickoff and organizer assignment. [Prior-work disclosure](docs/event-submission/README.md#prior-work-and-surprise-element) records what still needs owner confirmation. Do not present existing commits or synthetic data as event-built or real-market evidence without that check.

The website uses a white and gray research workspace over a restrained dither background. Fund disclosures, rankings, supporting signals, evaluation, and data management are available in the interface.

## Start locally

Requires Python 3.11+ and Node.js compatible with Vite 8 (Node 20.19+ or 22.12+). Open two PowerShell terminals at the repository root.

```powershell
cd backend
python -m pip install -r requirements.txt
$env:RISKORA_ADMIN_TOKEN = 'replace-with-a-long-local-secret'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. API documentation is at <http://127.0.0.1:8001/docs>. The Vite development server proxies `/api` to port 8001. Enter the same management token in **Data management**. It stays in this browser tab's memory and is sent to protected mutation endpoints.

## Demonstrate the full pipeline without a real dataset

1. Open **Data management**, enter the management token, and click **Load synthetic sample**. This loads two fictional schemes, 15 dated monthly snapshots per scheme, and fictional market observations into a separate `synthetic` data class.
2. Open **Fund explorer** and select a synthetic fund. Inspect the disclosed positions and changes.
3. Open **Evaluation**, choose **Synthetic sample** and the monthly period, then click **Train and evaluate**. This trains and evaluates on synthetic records only.
4. Open **Predictions** and rank candidates. Open a company to inspect its cutoff-dated inputs and supporting signals.

Synthetic evaluation numbers verify the code path; they do not measure predictive performance in Indian markets. No genuine model is bundled or pretrained.

## Explore the supplied ABSL Flexi Cap disclosures

The repository includes August and September 2026 AMC workbooks in `data/absl_flexi_cap/raw/` and their normalized holdings CSVs in `data/absl_flexi_cap/normalized/`. Run the following after installing `backend/requirements.txt`:

```powershell
python scripts/load_supplied_disclosures.py
```

The script validates both CSVs against their source workbooks, loads both snapshots into the local SQLite database, and is safe to rerun. Open **Fund explorer** and choose **ADITYA BIRLA SUN LIFE FLEXI CAP FUND**. August has 84 usable Indian-ISIN equity rows (98.4452% of AUM); September has 82 (97.8734%). Each workbook has one zero-value unlisted identifier outside the Indian ISIN format, which is omitted. The conversion keeps units, scales `% to AUM` fractions to percentage points, and converts market value from lakhs to rupees. See [the data review](docs/absl-data-review.md).

The workbooks were downloaded from the two AMC archive URLs in the [acquisition manifest](docs/absl-data-acquisition.md) and match the normalized data. Their exact public release dates remain unverified. The loader records its run date as the first observed availability date, links each snapshot to its AMC archive, and marks both ineligible for model labels. The dates appear as **Observed** in the explorer. The local database is ignored by Git, so another checkout must run the loader. Do not interpret the August-to-September difference as verified trading activity or real predictive performance.

## Import real disclosures

The first real-data path is a **user-normalized UTF-8 CSV import**. Download a public AMC or AMFI statement yourself, preserve its URL and publication date, and convert its equity holdings for a single scheme and report date into:

```csv
isin,company,weight,units,market_value,ticker,sector,industry
INE000A01010,Example Company,4.25,120000,55000000,EXAMPLE,Industrials,Capital Goods
```

`isin`, `company`, and `weight` (percentage, 0–100) are required. The other columns are optional; `units` are needed to distinguish accumulation from a mere weight increase. Upload one CSV per scheme per report date. Enter a stable scheme ID, exact scheme/AMC names, report date, **actual publication date**, public source URL, and attest whether the source represents a full comparable statement. Statements totaling under 90% weight are marked incomplete even if attested; totals over 101% are rejected. Duplicate ISINs, ambiguous ISIN/company names, and conflicting tickers are rejected. ISIN validation checks Indian format only, not the checksum or exchange registry. Originals are retained under `backend/data/uploads/` by SHA-256. Imports are classified `user_import`; the application does not automatically verify an uploaded file against its URL.

For market observations, import a UTF-8 CSV:

```csv
date,isin,company,close,adjusted_close,volume,ticker,sector,industry
2024-01-31,INE000A01010,Example Company,750.5,748.3,1234567,EXAMPLE,Industrials,Capital Goods
```

`date`, `isin`, `company`, `close`, and `volume` are required. An optional `source_url` column can identify the exact source archive for each row; otherwise the batch source URL is used. Dates and rows are validated; duplicate observations are rejected. Adjusted close is used for returns when supplied, otherwise raw close is used and the evidence notes that limitation. No live price API is called. `backend/app/ingestion.py` defines replaceable holdings and market provider protocols with working user CSV adapters. There is no automatic corporate-action, symbol-change, calendar, market/sector-index, or survivorship adjustment.

Public company events can be imported with `POST /api/v1/events` and then optionally extracted through `POST /api/v1/events/{id}/extract`. The latter is server side only. Without configured LLM credentials, events and all other workflows still work; extraction returns a clear configuration error. Facts and evidence must be verbatim substrings of the supplied excerpt. LLM output remains separate from original evidence.

### Source availability checked

- [AMFI Portfolio Disclosure](https://www.amfiindia.com/online-center/portfolio-disclosure) offers a disclosure selection interface. [AMFI scheme-wise disclosure](https://www.amfiindia.com/otherdata/scheme-wise-disclosure) is a separate quarterly selection view. These were checked as web pages; no programmatic historical download was tested.
- [AMFI-hosted scheme disclosure text](https://portal.amfiindia.com/spages/12306.pdf) describes monthly portfolio publication with ISIN on AMC and AMFI sites. Format and historical availability vary by AMC.
- [AMFI Monthly](https://www.amfiindia.com/research-information/amfi-monthly) publishes industry reports, which are **not** the same as scheme-level constituents.

The supplied August and September workbooks match the corresponding normalized CSVs and were retrieved through the AMC archive links in the acquisition manifest. Their release dates remain unverified. The pack can fetch NSE daily bhavcopies; one day was downloaded locally to check the adapter, but no NSE/BSE feed, market API, news feed, or hosted LLM endpoint was imported into the application. The normalized import route and synthetic path were tested locally. Do not label imported data as point-in-time verified without checking publication dates.

## Labels, features, and evaluation

For each scheme, the label builder pairs consecutive valid monthly disclosures, or the latest available disclosure in each calendar quarter. Monthly gaps must be 20–45 days; quarterly gaps 70–105 days. The earlier statement must have been published before the next report date. A candidate must be known through an already published holding or market observation at the cutoff. A new addition is absent in the earlier complete snapshot and present in the next complete snapshot at or above the chosen materiality threshold (default 0.1% weight). Verified absence is negative. Increased **units** of an existing holding produce `accumulation`; disappearance produces `exit`. Incomplete, missing, incomparable, or previously unknown cases are `unknown`, never negative. A weight increase alone is not treated as a buy.

Features include fund sector/industry weight preferences, concentration, prior observed additions, trailing market returns, volatility and volume ratio, and availability flags. Event direction enters the full model only if a validated extraction was processed by the cutoff. This strict cutoff means events imported and extracted today cannot retroactively enhance an old backtest. The candidate universe is restricted to securities known by the cutoff in the same data class.

`POST /api/v1/training-runs` fits a scikit-learn logistic classifier with preprocessing fitted on earlier dates only. At least four distinct comparable cutoff periods and both positive and negative training cases are required. Earlier dates are evaluated in expanding-window walk-forward folds; the final cutoff is held out independently. It compares a historical addition-frequency baseline, fund sector/industry preference baseline, a holdings+market model, and a full event model only when point-in-time event signals exist in both training and holdout data. Metrics are precision@5, recall@5, and average precision. Individual dated folds are available at `/api/v1/backtests`; the final holdout is shown separately. Probabilities are not calibrated, so Brier/calibration metrics and likelihood claims are intentionally absent. Performance across funds/sectors and survivorship bias are not yet robustly quantified. Artifacts and metrics are versioned under `backend/data/models/` and SQLite. Evidence includes signed logistic feature contributions to the model logit; they do not establish causality.

## Architecture and API

The frontend entry point mounts `Stage.tsx`, which places the supplied WebGL dither behind the research interface in `App.tsx`. API contracts are in `domain.ts`; request handling is in `api.ts` and `hooks/`; shared controls and tables are in `components/`; the six screens are in `pages/`. The light theme is in `stage.css`. See [the implementation audit](docs/implementation-audit.md) for the earlier interface analysis and decisions.

### Publication-aware model version

New runs use `logistic-v2`. Each validation/holdout split excludes training examples whose **target statement was not yet published at the evaluation cutoff**. Readiness uses the same availability and class checks as training. Predictions also check label availability at their cutoff and refuse a latest incomplete statement instead of falling back to older positions.

Existing `logistic-v1` runs remain viewable with a legacy warning. They are excluded from new rankings; **retrain each dataset and period** before generating new results. Prediction responses include `published_at` and `generated_at` separately from report date and information cutoff. Backtest responses include `run_id`; the interface always requests an explicit run.

The React/Vite entry point is `frontend/src/main.tsx` → `Stage.tsx` → `App.tsx`. The FastAPI entry point is `backend/app/main.py` under `/api/v1`. SQLite storage lives in `backend/app/db.py`; imports in `ingestion.py`; features, labels, models, and ranking in `ml.py`; optional LLM extraction in `signals.py`.

Read endpoints: `/health`, `/api/v1/overview`, `/funds`, `/funds/{id}`, `/identifiers`, `/market`, `/events`, `/readiness`, `/training-runs`, `/backtests`, `/predictions/{fund}`, `/evidence/{fund}/{isin}`. Protected write endpoints: `/api/v1/imports/holdings`, `/imports/market`, `/identifiers/{isin}` (PUT), `/events`, `/events/{id}/extract`, `/training-runs`, `/demo/load`. See `/docs` for fields. Protected endpoints require `X-Admin-Token` equal to server-side `RISKORA_ADMIN_TOKEN`; if unset, management actions are disabled. Uploads have a 5 MB/read and 20,000-row limit. Source URLs are stored as provenance and are never fetched by the server.

## Configuration

Copy `backend/.env.example` as a reference and set variables in the backend process environment. The application does not auto-load a `.env` file.

| Variable | Purpose |
| --- | --- |
| `RISKORA_ADMIN_TOKEN` | Required for mutations; choose a long random secret. |
| `RISKORA_DB` | SQLite path; default `backend/data/riskora.sqlite3`. |
| `RISKORA_UPLOAD_DIR` | Original CSV storage; default `backend/data/uploads`. |
| `CORS_ORIGINS` | Comma-separated allowed browser origins. |
| `RISKORA_AUTO_LOAD_SYNTHETIC` | When true, seed the clearly labelled fictional sample at startup (demo hosting only). |
| `RISKORA_AUTO_TRAIN_SYNTHETIC` | When true, create a monthly synthetic evaluation and model at startup if one is missing (demo hosting only). |
| `LLM_BASE_URL` | Optional OpenAI-compatible HTTPS endpoint root; `/chat/completions` is appended. |
| `LLM_API_KEY` | Optional server-only inference key. |
| `LLM_MODEL` | Optional model ID. |

The LLM request uses JSON mode. A compatible Neysa endpoint can be configured if it implements the same route and response shape. Neither Neysa nor any other hosted endpoint was tested here.

## Verify

```powershell
cd backend
python -m pytest -q
cd ..\frontend
npm test
npm run lint
npm run format:check
npm run build
```

Known limitations: the supplied ABSL `.xls` can be normalized by `scripts/normalize_absl_xls.py`, but other disclosure layouts and PDFs still need manual conversion; completeness is partly user attested; there is no automatic AMC/AMFI discovery, price/news ingestion, corporate-action audit, probability calibration, continuous background refresh, or credible real-data backtest without more verified historical disclosures. Local SQLite and a single management token suit a local demonstration, not multi-user production deployment.

## One-service public demo

The root `Dockerfile` and `render.yaml` build React and serve it with FastAPI from one URL. The Render free-demo configuration recreates and trains **fictional synthetic data only** on startup. See the [Render deployment guide](docs/DEPLOY-RENDER-SIMPLE.md). Its `/tmp` database, uploads, and models are ephemeral; use [persistent hosting](docs/hosting-live.md) for data you need to keep.
