# RISVANTA — Complete Frontend Build Specification

> **Purpose:** Build the complete frontend for Risvanta, a global, AI-powered portfolio risk-intelligence platform. This document is the single source of truth for the frontend implementation.
>
> **Scope:** Frontend only. Do not implement the backend, database, authentication server, market-data service, financial calculations API, or AI service in this task. Use a clean API service layer with realistic mock data so the frontend runs independently and can later connect to the backend.

---

## 1. Product overview

### Product name
**Risvanta**

### Product category
Global portfolio risk intelligence.

### Core positioning
**See beyond the returns.**

Risvanta helps users understand what they own, discover hidden exposure across stocks and funds, simulate market and currency shocks, and understand the evidence behind each risk finding.

### Main user journey
1. Open the dashboard.
2. Load the clearly labelled demo portfolio or enter holdings.
3. Review portfolio allocation and hidden exposure.
4. Choose a market or currency stress scenario.
5. Run the scenario.
6. Inspect estimated portfolio impact and the assets or sectors driving it.
7. Open an explanation that shows assumptions, dates, and source references.

### Product principles
- Global by default. Do not hard-code India-only concepts, currency, exchanges, or markets into the layout.
- Risk education and scenario analysis, not buy/sell recommendations.
- Every simulated result must be labelled as an estimate, not a prediction.
- Distinguish live data from mock/demo data.
- Show currencies and units explicitly.
- Make assumptions and source dates easy to find.
- Do not use AI-generated text as the source of numerical truth.
- Never imply that a demo portfolio or sample holding belongs to the current user.
- Do not fabricate live prices, news, source links, or data freshness.

---

## 2. Required frontend stack

Use the following unless the existing repository already has a compatible stack. If a repository exists, inspect it first and preserve its conventions rather than replacing it unnecessarily.

- **React**
- **Vite**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** for accessible interface primitives
- **Lucide React** for icons
- **Recharts** for charts
- **React Router** for page routing
- **Zod** for validating frontend form inputs and API responses
- **React Hook Form** for forms
- **TanStack Query** for async API state if API integration is implemented
- **Vitest** and **React Testing Library** for important UI tests

Avoid adding large libraries without a concrete need. Use the package manager already present in the repository.

### Initial setup (if starting from an empty directory)

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom lucide-react recharts zod react-hook-form @hookform/resolvers
npm install @tanstack/react-query
npm install -D tailwindcss @tailwindcss/vite vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Set up Tailwind using the installation instructions for the version selected. Add shadcn/ui only if its setup is compatible with the existing project. Do not paste deprecated setup commands without checking the installed Tailwind version.

Run the application with:

```bash
npm run dev
```

---

## 3. Visual design direction

### Design goal
Create a polished, credible financial-data product. The interface should feel like a modern analytical workspace: precise, calm, dense enough to be useful, and easy to scan.

Avoid:
- Generic AI landing-page gradients everywhere
- Glassmorphism on every card
- Excessive rounded pills
- Huge decorative headings in the dashboard
- Fake live tickers and fake “real-time” badges
- Random gradients, emoji icons, or decorative illustrations
- Dense tables with no spacing or responsive handling
- Red/green as the only way to communicate meaning

### Theme
Use a dark-first analytical dashboard with an optional light theme if time permits.

Suggested dark palette:
- App background: `#0B0D12`
- Sidebar: `#10131A`
- Surface/card: `#151923`
- Raised surface: `#1B202B`
- Border: `#292F3D`
- Primary text: `#F3F5F8`
- Secondary text: `#A1A9B8`
- Muted text: `#727B8D`
- Accent violet: `#A78BFA`
- Accent mint: `#B8F7D4`
- Risk/warning: `#F5B96B`
- Negative impact: `#FF7D87`
- Positive impact: `#70D6A6`
- Focus ring: `#B8A1FF`

Use CSS variables/tokens so colors can be changed centrally. Confirm contrast for text, chart labels, focus indicators, and controls. Never depend on color alone; pair color with labels, icons, or signed values.

### Typography
Use a clean UI font such as Inter, Geist, or the project's existing font. Use a clear type scale:
- Page title: 24–30 px
- Section heading: 16–20 px
- Card metric: 24–32 px
- Body: 14–16 px
- Supporting labels: 12–13 px

Use tabular numerals for money and percentage values when available.

### Layout
- Desktop: fixed-width collapsible sidebar, top bar, main content with a comfortable max-width.
- Tablet: collapsible sidebar or drawer.
- Mobile: compact header, drawer navigation, single-column cards, horizontally scrollable chart/table regions where necessary.
- Keep content readable at 360 px width.
- Use consistent spacing, border, radius, and card elevation.
- Include visible hover, focus, active, disabled, loading, empty, and error states.

### Logo treatment
Use a simple text wordmark **RISVANTA** with a small geometric mark built from CSS or Lucide (for example, a layered/radar motif). Do not depend on a remote logo asset. The mark must be simple enough to recreate in SVG later.

---

## 4. Navigation and routes

Implement the following routes:

| Route | Page | Purpose |
|---|---|---|
| `/` | Overview dashboard | Portfolio summary and key risk findings |
| `/portfolio` | Portfolio | Holdings list, add/edit/delete holdings, import CSV UI |
| `/exposure` | Exposure analysis | Asset, sector, company, geography, and currency exposure |
| `/stress-test` | Stress testing | Choose scenario and inspect estimated portfolio impact |
| `/insights` | Risk insights | Evidence-backed explanations and risk drivers |
| `/settings` | Settings | Display preferences, currency, demo-data controls, and disclaimer |

Use a shared application shell for all authenticated-style pages, but **do not implement authentication**. Treat the prototype as a single local demo workspace. If an unknown route is opened, show a branded not-found page with a link back to the dashboard.

### Sidebar
- Overview
- Portfolio
- Exposure
- Stress tests
- Risk insights
- Settings

At the bottom:
- “Demo workspace” status
- Small data-mode label such as `DEMO DATA`
- User avatar placeholder labelled “Demo user” (do not invent a real identity)

### Top bar
- Current page title/breadcrumb
- Portfolio selector (initially one demo portfolio; selection should work if multiple local mock portfolios are included)
- Data status label: `Sample data` when using mocks
- Base currency selector
- Notifications icon only if it has a real local interaction; otherwise omit it
- Theme toggle if both themes are implemented

---

## 5. Overview dashboard (`/`)

Build a high-quality dashboard that immediately communicates portfolio composition and downside risk.

### Header
Title: **Portfolio overview**
Subtitle: “Understand your exposure before the market moves.”
Actions:
- `Add holding`
- `Run stress test`
- `Load demo portfolio` if no portfolio is loaded

Show a persistent but non-alarming demo-data banner:
> You’re viewing illustrative sample data. Results are not live market data or investment advice.

### Summary metric cards
1. **Portfolio value**
   - Total value in the selected base currency.
   - Show the base currency clearly.
   - If a previous-value comparison is mock data, label it as illustrative.
2. **Assets tracked**
   - Number of unique holdings, not number of rows if duplicates are merged.
3. **Largest sector exposure**
   - Sector name and percentage of portfolio.
4. **Scenario downside**
   - Estimated impact for the currently selected scenario.
   - Label as “simulated” or “estimated”, never “expected loss”.

### Main chart area
- Allocation chart (donut or horizontal bar) by asset class.
- Holdings/exposure table showing top companies or assets.
- Chart must have a visible legend, values, and accessible text alternative.
- Tooltip should show absolute value, percentage, and currency.
- If chart data is empty, show a helpful empty state and an action to add holdings.

### Risk highlights
Create three or four insight cards derived from mock calculations, for example:
- “Concentration: Your largest sector accounts for 32% of the sample portfolio.”
- “Overlap: Two funds share exposure to the same underlying company.”
- “Currency: A USD/GBP movement may affect the base-currency value of foreign holdings.”
- “Scenario: The selected market shock has the largest estimated impact on [asset/sector].”

Only display an insight if the supporting mock data exists. Do not use absolute claims like “your portfolio is unsafe.”

### Recent scenarios
List the last few local scenario runs:
- Scenario name
- Date/time label clearly marked as local demo history
- Estimated impact
- `View results` action

Persist only local prototype state if desired. If persistence is not implemented, keep the history in memory and label it as session-only.

---

## 6. Portfolio page (`/portfolio`)

### Purpose
Let the user inspect and edit a sample portfolio without requiring a backend.

### Required interactions
- Load demo portfolio.
- Add a holding.
- Edit a holding.
- Delete a holding after confirmation.
- Search holdings by name or ticker.
- Filter by asset class and currency.
- Sort by name, market value, or weight.
- Switch between table and compact list view if time permits.
- Show a useful empty state.
- CSV import panel with file selection and validation feedback. If parsing is not implemented, make the limitation explicit and do not pretend the import succeeded.

### Holding fields
Use a typed model:

```ts
type AssetClass =
  | "stock"
  | "etf"
  | "mutual_fund"
  | "bond"
  | "cash"
  | "other";

type Holding = {
  id: string;
  name: string;
  ticker?: string;
  assetClass: AssetClass;
  quantity?: number;
  marketValue: number;
  currency: string;
  country?: string;
  sector?: string;
  sourceLabel: string;
  asOfDate: string;
  isDemo: boolean;
};
```

`marketValue` is expressed in the holding's own currency unless the app explicitly stores a base-currency value separately. Do not add values in different currencies without conversion. For the initial demo, include `baseCurrencyValue` in mock data and explain that it is an illustrative converted value.

### Add/edit holding form
Fields:
- Asset name (required)
- Ticker/symbol (optional)
- Asset class (required)
- Market value (required, positive number)
- Holding currency (required; use a sensible list such as USD, EUR, GBP, INR, JPY, CAD, AUD, CHF)
- Country/market (optional)
- Sector (optional)
- Quantity (optional)
- Data source label (required for demo transparency; default `User-entered`)
- As-of date (required; default today for user-entered mock input, but do not imply that market prices are live)

Validation:
- Name cannot be blank.
- Market value must be a finite number greater than zero.
- Currency must be selected.
- Do not allow `NaN`, infinity, or invalid negative quantities.
- Display errors next to the relevant fields.
- Do not silently change user input.

### Holdings table columns
- Asset
- Asset class
- Country/market
- Currency
- Market value
- Base-currency value (if available)
- Portfolio weight
- Data date/source
- Actions

On mobile, switch to stacked holding cards rather than squeezing every column.

### Demo portfolio
Use fictional or clearly labelled illustrative holdings, e.g.:
- Northstar Global Equity ETF — ETF — USD
- Atlas Technology Fund — mutual fund — USD
- Meridian Global Fund — mutual fund — EUR
- Example Semiconductor Co. — stock — USD
- Example Infrastructure Group — stock — INR
- Global Treasury Basket — bond — USD
- Cash Reserve — cash — EUR

Avoid implying that fictional company names are actual securities. Add `Illustrative sample asset` where needed. Keep numbers internally consistent and deterministic.

---

## 7. Exposure analysis page (`/exposure`)

### Purpose
Reveal the portfolio's underlying composition and hidden concentration.

### Exposure views
Use tabs or a segmented control:
- Asset class
- Sector
- Underlying company
- Geography
- Currency

Each view should show:
- Exposure amount in base currency
- Percentage of total portfolio
- Number of holdings contributing
- A chart and a detail table
- Data freshness/source information where available

### Look-through exposure
Represent mutual-fund holdings as underlying weights in mock data. Aggregate exposure using deterministic calculations.

Example:
- Fund A market value: 10,000 base-currency units
- Underlying Company X weight: 20%
- Exposure through Fund A: 2,000 base-currency units
- Fund B market value: 5,000 base-currency units
- Underlying Company X weight: 10%
- Exposure through Fund B: 500 base-currency units
- Direct holding in Company X: 1,000 base-currency units
- Total Company X exposure: 3,500 base-currency units

The table must show the breakdown:
- Direct holding exposure
- Fund A contribution
- Fund B contribution
- Total look-through exposure

Label look-through data as **illustrative** if it is not from a verified published fund holdings file. Never imply the fund composition is live or official when it is mock data.

### Overlap insight
Highlight companies or sectors appearing through multiple funds and direct holdings.
- Show how the total was calculated.
- Avoid saying overlap is inherently bad.
- Explain that overlap can create concentration and may be intentional.
- Add a “How this is calculated” expandable panel.

### Currency exposure
Show:
- Exposure by currency
- Foreign-currency exposure as a share of portfolio
- The base currency used for comparison
- An explanatory note that currency movements can increase or decrease base-currency returns depending on asset-price changes and exchange-rate movements.

---

## 8. Stress testing page (`/stress-test`)

### Purpose
Let users simulate transparent hypothetical shocks and inspect the estimated impact.

### Scenario selector
Provide presets:
1. Broad market decline
2. Technology sector decline
3. USD strengthens against base currency
4. USD weakens against base currency
5. Combined market and currency shock
6. Custom scenario

For each preset, display:
- Scenario description
- Shock assumptions
- A clear `Hypothetical scenario` label
- Whether the shock affects asset prices, FX rates, or both

### Controls
- Select scenario
- Choose base currency
- Adjust shock percentage with a slider or numeric input
- Choose affected sectors/assets if custom scenario is selected
- `Run simulation` button
- `Reset` button

### Result layout
After running:
- Portfolio value before scenario
- Estimated portfolio value after scenario
- Estimated absolute change
- Estimated percentage change
- Breakdown by asset, company, sector, and currency where data supports it
- Top contributors to the simulated loss or gain
- Scenario assumptions
- Calculation methodology
- Data dates and sources

### Calculation requirements
Use a frontend calculation module for the prototype, with unit tests. Keep it isolated so it can later be replaced by the backend API.

For a simple price shock:

```ts
estimatedChange = exposedBaseValue * shockReturn;
estimatedPostShockValue = currentBaseValue + estimatedChange;
```

For a foreign-currency asset, use a clearly defined conversion convention. If `fxRate` means units of base currency per one unit of foreign currency:

```ts
baseValue = foreignValue * fxRate;
```

If asset return is `rAsset` and FX return is `rFx` under that convention:

```ts
combinedReturn = (1 + rAsset) * (1 + rFx) - 1;
```

Do not add the two returns directly when compounding matters. Document the sign convention in code and UI.

For a portfolio with multiple currencies, do not sum original-currency values directly. Convert each position to the selected base currency first, using the demo's declared exchange-rate assumptions.

### Important scenario semantics
- A 10% market decline is a hypothetical input, not a prediction.
- If USD strengthens versus the selected base currency, an unhedged USD asset may gain base-currency value if its USD price is unchanged.
- If the underlying foreign asset also falls, the currency move may offset some or all of that decline; calculate the combined effect.
- Do not describe all currency changes as losses.
- Do not describe the result as Value at Risk (VaR) unless a statistically appropriate method is actually implemented.
- Do not use “probability” or “confidence level” unless those values are actually calculated and supported.
- If a holding has no relevant exposure mapping, show “Not modelled in this scenario” rather than assuming an impact of zero without explanation.

### Result breakdown table
Columns:
- Asset/sector/currency
- Current base-currency exposure
- Applied shock
- Estimated change
- Estimated post-shock value
- Assumption/source

Include a compact methodology accordion and a disclaimer beneath results.

---

## 9. Risk insights page (`/insights`)

### Purpose
Explain risk findings using transparent evidence rather than unsupported AI claims.

### Insight cards
Each insight must include:
- Title
- Severity label (`Info`, `Moderate`, `High`) only if a deterministic rule defines it
- Plain-language explanation
- Evidence or calculation
- Related holdings
- Data as-of date
- Source label and source URL if available
- `View calculation` interaction
- `Ask about this insight` interaction

### Example insight
**Repeated exposure to one company**

“Company X represents 18% of the illustrative portfolio when direct holdings and look-through fund exposure are combined. This concentration means that a company-specific shock could have a larger portfolio effect than its direct holding alone suggests.”

Show the underlying numbers and fund contributions. This should be generated from mock calculation results, not written as an unverified claim.

### AI explanation panel
Build the frontend UI only:
- Text input with placeholder “Ask why this scenario affects the portfolio…”
- Suggested prompts:
  - “Which holdings drive this result?”
  - “How does currency affect the outcome?”
  - “Show me the overlap calculation.”
  - “What assumptions did this scenario use?”
- Answer area
- Source chips/links
- Loading, empty, error, and unavailable states

Until a backend AI endpoint exists, use a local deterministic response function that selects from known mock explanations. Add a visible label: `Prototype explanation — not connected to an AI service`. Do not present hard-coded text as a live AI answer.

### Evidence drawer
When a source or calculation is selected, open a side drawer/modal showing:
- Finding
- Calculation details
- Inputs used
- Assumptions
- Source name
- Source URL (only if a real URL is present in the data)
- Reporting/as-of date
- Data status: `Illustrative`, `User-entered`, or `Verified source`

Never invent a source URL. If no URL exists, show `No external source linked`.

---

## 10. Settings page (`/settings`)

Include:
- Base currency selector
- Number-format preference
- Theme selector if light mode exists
- Demo portfolio reload/reset action with confirmation
- Data-mode explanation
- Privacy note
- Risk disclaimer
- About Risvanta section

### Disclaimer copy
Use this wording or a substantively equivalent one:

> Risvanta is a portfolio risk-education prototype. Scenario outputs are hypothetical estimates based on the displayed inputs and assumptions. They are not predictions, guarantees, or personalized investment advice. Data may be illustrative or delayed and must be checked against the stated source and date. Consult a qualified professional for advice suited to your circumstances.

Do not claim regulatory approval, financial-adviser status, institutional-grade accuracy, or real-time market data.

---

## 11. Shared components

Create reusable components instead of duplicating markup.

Suggested structure:

```text
src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers.tsx
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Topbar.tsx
│   │   └── MobileNavigation.tsx
│   ├── common/
│   │   ├── PageHeader.tsx
│   │   ├── DemoDataBanner.tsx
│   │   ├── MetricCard.tsx
│   │   ├── CurrencyValue.tsx
│   │   ├── PercentValue.tsx
│   │   ├── SourceBadge.tsx
│   │   ├── EmptyState.tsx
│   │   ├── ErrorState.tsx
│   │   ├── LoadingState.tsx
│   │   ├── ConfirmDialog.tsx
│   │   └── MethodologyAccordion.tsx
│   ├── portfolio/
│   │   ├── HoldingsTable.tsx
│   │   ├── HoldingForm.tsx
│   │   └── CsvImportPanel.tsx
│   ├── exposure/
│   │   ├── ExposureChart.tsx
│   │   ├── ExposureTable.tsx
│   │   └── OverlapBreakdown.tsx
│   ├── stress-test/
│   │   ├── ScenarioSelector.tsx
│   │   ├── ScenarioControls.tsx
│   │   ├── ScenarioSummary.tsx
│   │   └── ImpactBreakdown.tsx
│   └── insights/
│       ├── InsightCard.tsx
│       ├── ExplanationPanel.tsx
│       └── EvidenceDrawer.tsx
├── pages/
│   ├── OverviewPage.tsx
│   ├── PortfolioPage.tsx
│   ├── ExposurePage.tsx
│   ├── StressTestPage.tsx
│   ├── InsightsPage.tsx
│   ├── SettingsPage.tsx
│   └── NotFoundPage.tsx
├── data/
│   ├── demoPortfolio.ts
│   ├── demoFundHoldings.ts
│   ├── demoFxRates.ts
│   ├── demoScenarios.ts
│   └── demoSources.ts
├── lib/
│   ├── formatters.ts
│   ├── validation.ts
│   └── utils.ts
├── services/
│   ├── apiClient.ts
│   ├── portfolioService.ts
│   ├── exposureService.ts
│   ├── scenarioService.ts
│   └── insightService.ts
├── types/
│   ├── portfolio.ts
│   ├── exposure.ts
│   ├── scenario.ts
│   └── insight.ts
├── hooks/
│   ├── usePortfolio.ts
│   └── useScenario.ts
├── test/
│   └── setup.ts
├── index.css
└── main.tsx
```

The exact folder structure may be adapted to the repository, but preserve clear separation between UI, data, calculation logic, and API integration.

---

## 12. API-ready service layer

Even though the backend is out of scope, do not scatter mock objects throughout components. Keep all data access behind service functions.

Create an environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Do not commit secrets. Do not put API keys in frontend environment variables; Vite-exposed variables are public in the browser bundle.

Create service functions with a mock fallback:
- `getPortfolio()`
- `saveHolding(holding)`
- `updateHolding(id, patch)`
- `deleteHolding(id)`
- `getExposure(baseCurrency)`
- `runScenario(request)`
- `getInsights()`
- `askInsightQuestion(request)`

Recommended behaviour:
1. `VITE_USE_MOCK_DATA=true` uses local mock implementations.
2. When mock mode is off, use `VITE_API_BASE_URL`.
3. If the backend is unavailable, show a clear error or an explicitly labelled mock fallback. Never silently swap to fabricated data while showing a live-data status.
4. Keep the response types in `src/types`.
5. Add request timeout/error handling if using a network client.
6. Show loading, success, empty, and error states.

Suggested `.env.example`:

```env
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:8000
```

If API integration is not ready, the complete frontend must still work in mock mode.

---

## 13. TypeScript domain types

Define explicit types and avoid `any`.

```ts
export type CurrencyCode =
  | "USD"
  | "EUR"
  | "GBP"
  | "INR"
  | "JPY"
  | "CAD"
  | "AUD"
  | "CHF";

export type AssetClass =
  | "stock"
  | "etf"
  | "mutual_fund"
  | "bond"
  | "cash"
  | "other";

export type DataStatus =
  | "illustrative"
  | "user_entered"
  | "verified_source"
  | "delayed";

export interface Holding {
  id: string;
  name: string;
  ticker?: string;
  assetClass: AssetClass;
  quantity?: number;
  marketValue: number;
  currency: CurrencyCode;
  country?: string;
  sector?: string;
  baseCurrencyValue?: number;
  sourceLabel: string;
  sourceUrl?: string;
  asOfDate: string;
  dataStatus: DataStatus;
  isDemo: boolean;
}

export interface FundConstituent {
  fundId: string;
  underlyingAssetId: string;
  underlyingName: string;
  weight: number; // Decimal from 0 to 1, not percentage points.
  sector?: string;
  currency: CurrencyCode;
  asOfDate: string;
  dataStatus: DataStatus;
}

export type ScenarioType =
  | "market"
  | "sector"
  | "fx"
  | "combined"
  | "custom";

export interface ScenarioRequest {
  scenarioId: string;
  baseCurrency: CurrencyCode;
  assetShockPercent?: number;
  fxShockPercent?: number;
  affectedSector?: string;
  affectedAssetIds?: string[];
}

export interface ScenarioImpactRow {
  id: string;
  name: string;
  exposureBaseValue: number;
  assetReturn?: number;
  fxReturn?: number;
  estimatedChangeBaseValue: number;
  postShockBaseValue: number;
  explanation: string;
  dataStatus: DataStatus;
}

export interface ScenarioResult {
  scenarioId: string;
  baseCurrency: CurrencyCode;
  portfolioValueBefore: number;
  portfolioValueAfter: number;
  estimatedChange: number;
  estimatedChangePercent: number;
  assumptions: string[];
  asOfDate: string;
  rows: ScenarioImpactRow[];
  isSimulation: true;
}

export interface EvidenceSource {
  id: string;
  label: string;
  url?: string;
  asOfDate?: string;
  dataStatus: DataStatus;
}

export interface RiskInsight {
  id: string;
  title: string;
  severity: "info" | "moderate" | "high";
  summary: string;
  details: string;
  relatedHoldingIds: string[];
  calculationDescription: string;
  sources: EvidenceSource[];
  dataStatus: DataStatus;
}
```

Use one consistent convention for percentages:
- UI inputs may display percentage points such as `-10%`.
- Internal return values may use decimals such as `-0.10`.
- Convert at the input/output boundary.
- Add tests to prevent accidental mixing.

---

## 14. Number and currency formatting

Use `Intl.NumberFormat`; do not manually add currency symbols.

Example:

```ts
export function formatCurrency(
  amount: number,
  currency: string,
  locale = "en-US",
) {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatPercent(value: number, digits = 1) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}
```

Be explicit about whether a value is stored as `0.1` or `10`. The above percentage formatter expects `0.1` to display `10%`.

Do not display an unlabelled currency value. If the value is a converted estimate, show the base currency and that the FX conversion is illustrative where appropriate.

---

## 15. Demo data requirements

Create deterministic mock data for:
- One global demo portfolio
- At least 7 holdings across multiple asset classes and currencies
- At least 2 funds with overlapping underlying assets
- Underlying company and sector mappings
- FX rates for every foreign currency used by the portfolio
- At least 5 stress scenarios
- At least 3 risk insights with calculation details
- Sources/data-status metadata
- A few recent demo scenario runs

The mock data must be internally consistent. Do not invent real securities or imply sample data comes from a real fund. Prefer fictional sample names, or use actual securities only when their identity and data source are verified.

### Required sample scenario
Include a broad-market shock and an FX shock. Show how the estimated impact is calculated.

For each scenario, store:
- Scenario name
- Description
- Shock assumptions
- Affected assets/sectors/currencies
- Calculation method
- Data status
- As-of date

If a scenario cannot reasonably affect a holding based on available mappings, mark it `Not modelled` rather than silently treating it as unaffected.

---

## 16. Frontend calculation module

Create pure functions, independent of React, for:
- Calculating portfolio totals in the selected base currency
- Calculating portfolio weights
- Aggregating asset-class/sector/currency exposure
- Calculating look-through fund exposure
- Detecting overlapping underlying assets
- Calculating market-shock impacts
- Calculating FX impacts
- Combining asset and FX returns
- Producing a scenario breakdown
- Generating deterministic mock explanations from results

Do not bury financial calculations inside components or React hooks. Keep them in a dedicated module such as `src/lib/riskCalculations.ts`.

### Minimum correctness rules
- Validate all inputs.
- Reject missing or invalid FX conversion assumptions.
- Do not add values in different currencies without converting them.
- Fund constituent weights should be between 0 and 1.
- Explain if fund constituent weights do not sum to 1; do not silently normalize unless explicitly intended and documented.
- Use the same shock convention in charts, tables, and explanatory text.
- Ensure portfolio value after scenario equals value before plus estimated change, within a defined floating-point tolerance.
- Display rounding only at presentation time; keep calculations at full numeric precision.
- Keep the source and as-of date attached to every derived result where possible.

---

## 17. Accessibility and responsive behaviour

- Use semantic HTML.
- Every input has a visible label.
- Icon-only buttons have accessible names.
- All controls are keyboard accessible.
- Focus indicators are clearly visible.
- Dialogs/drawers manage focus correctly.
- Charts have accessible labels or an equivalent data table.
- Use status text and icons as well as color.
- Respect reduced-motion preferences.
- Do not use animation that delays access to essential data.
- Tables remain usable on mobile.
- Buttons and interactive targets are comfortably tappable.
- Errors explain how to fix the problem.

---

## 18. Loading, empty, and error states

Implement the following states deliberately:

### No portfolio
Message: “Your portfolio is empty.”
Action: `Load demo portfolio` or `Add your first holding`.

### Loading
Use restrained skeletons that match the eventual content. Do not show fake values while loading.

### Backend unavailable
Message: “We couldn't connect to the analysis service.”
Actions: `Retry` and, only if configured, `Use demo mode`.

### Missing source data
Message: “This exposure could not be verified with the available data.”
Show the data that is available and explain the limitation.

### Invalid scenario
Explain which input is invalid and preserve the user's other inputs.

### Empty chart
Show a concise explanation and a direct action. Never render a broken or misleading empty graph.

### AI service unavailable
Show: “Explanations are unavailable right now.” Keep calculations and scenario results visible.

---

## 19. Privacy and safety requirements

- Do not request bank login credentials, brokerage passwords, API keys, or account access.
- Do not transmit portfolio data anywhere in mock mode.
- Do not add analytics/tracking by default.
- Do not put private portfolio information in URLs or logs.
- Do not claim data is encrypted at rest or in transit unless the relevant infrastructure actually provides it.
- Do not recommend buying or selling assets.
- Do not label a portfolio “safe” or “unsafe”.
- Do not represent stress scenarios as forecasts.
- Clearly distinguish estimates, mock data, user-entered data, and verified external sources.
- Do not expose server-side secrets in the frontend.

---

## 20. Testing checklist

Write tests for the pure calculation functions and important interactions.

### Calculation tests
- Portfolio weight totals are approximately 100% when all holdings are valued in the same base currency and included in the denominator.
- Holdings in different currencies are converted before aggregation.
- Overlapping fund exposure adds correctly.
- Direct exposure plus look-through exposure is not double-counted.
- A `-10%` shock on a 20,000 base-currency exposure produces a `-2,000` estimated change.
- FX appreciation and depreciation both work with the declared conversion convention.
- Combined asset and FX returns use compounding.
- Missing FX rates produce an explicit unmodelled/error result.
- Invalid constituent weights are rejected or clearly reported.
- Scenario post-value reconciles with pre-value plus change.

### UI tests
- Sidebar routes work.
- Demo portfolio loads.
- Add/edit/delete holding works.
- Search and filters work.
- Invalid form input displays useful validation.
- Scenario controls update the selected assumptions.
- Running a scenario displays its result.
- Source drawer displays the correct source metadata.
- Mobile navigation can open and close.
- Empty, loading, and error states are rendered.

### Manual browser QA
- Test at 1440 px desktop, 768 px tablet, and 360 px mobile.
- Verify no horizontal page overflow.
- Verify chart labels and tooltips remain legible.
- Verify no console errors.
- Verify direct navigation to each route.
- Verify refresh does not break routing in the intended deployment environment.

---

## 21. Performance and code quality

- Use small, reusable components.
- Avoid giant single-file components.
- Use stable React keys.
- Avoid unnecessary re-renders and expensive repeated calculations.
- Use memoization only where it provides a clear benefit.
- Avoid network calls from presentation components.
- Keep calculations deterministic and testable.
- Do not ignore TypeScript errors or disable strict checking to get a build.
- Do not add dependencies for features that can be handled simply.
- Add useful comments to non-obvious financial conventions.
- Remove dead code, placeholder buttons, and console debugging before submission.

---

## 22. Implementation order

Follow this order so the frontend stays runnable throughout development.

### Phase 1 — App foundation
- Inspect existing repository and package manager.
- Set up React/TypeScript routing.
- Build theme tokens and app shell.
- Build sidebar, topbar, responsive navigation and reusable page header.
- Confirm all routes render.

### Phase 2 — Data and types
- Add TypeScript models.
- Add deterministic demo portfolio, fund holdings, FX assumptions, scenarios, and source metadata.
- Add formatting and validation helpers.
- Add mock service functions.

### Phase 3 — Portfolio management
- Build holdings list/table.
- Build add/edit form.
- Implement search, filters, sort and delete confirmation.
- Implement demo load/reset.
- Add CSV import UI with honest status.

### Phase 4 — Risk calculations
- Implement portfolio totals, base-currency conversion, weights, look-through, overlap and scenario math as pure functions.
- Add unit tests.
- Verify example calculations manually.

### Phase 5 — Dashboard and exposure
- Build overview metrics and charts.
- Build asset-class, sector, company, geography and currency exposure views.
- Add overlap breakdown and calculation explanation.

### Phase 6 — Stress tests
- Build scenario selector and controls.
- Run deterministic frontend calculations.
- Show result summary, breakdown table, assumptions and disclaimer.
- Add recent scenario history.

### Phase 7 — Insights and evidence
- Build insight cards.
- Build calculation/source drawer.
- Build prototype explanation panel with clear mock-AI label.
- Do not invent sources.

### Phase 8 — Polish and QA
- Add loading, empty and error states.
- Check mobile responsiveness and accessibility.
- Fix console/build/test issues.
- Write the README.
- Verify that demo mode works without the backend.

---

## 23. Definition of done

The frontend is complete when all of the following are true:

- [ ] The app runs locally using the documented commands.
- [ ] All six main routes work.
- [ ] The visual design is consistent and responsive.
- [ ] Demo portfolio data is clearly labelled.
- [ ] Users can add, edit, delete, search, filter and sort holdings.
- [ ] Portfolio values and weights use a consistent base currency.
- [ ] Fund look-through and overlap views show their calculations.
- [ ] Market and FX stress scenarios run and show a transparent breakdown.
- [ ] Combined asset/FX returns use a consistent convention.
- [ ] The explanation panel never pretends mock text is live AI.
- [ ] Source metadata and as-of dates are visible where available.
- [ ] Every scenario result is labelled as an estimate.
- [ ] Empty, loading, validation and error states are implemented.
- [ ] The frontend does not require the backend to run in demo mode.
- [ ] Important calculation and interaction tests pass.
- [ ] No placeholder buttons falsely imply a completed action.
- [ ] No fabricated live data or source URLs are displayed.
- [ ] README includes setup, environment variables, routes, mock-data behaviour and known limitations.

---

## 24. README content required

Create a project README containing:
1. Project name and one-sentence description.
2. Main features.
3. Frontend tech stack.
4. Prerequisites.
5. Installation and run commands.
6. Environment variables.
7. Route overview.
8. How demo data works.
9. How scenario calculations are represented.
10. How to connect the frontend to the future backend.
11. Test commands.
12. Current limitations and disclaimer.

Suggested scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

Adapt these scripts to the repository's actual Vite/TypeScript setup rather than overwriting working configuration blindly.

---

## 25. Final instruction to the coding agent

Build the **complete frontend**, not just a landing page or static dashboard screenshot.

Before writing code:
1. Inspect the existing repository.
2. Identify the current stack and preserve working setup.
3. Create a short implementation checklist.
4. Implement the application in the phases above.
5. Keep the project runnable after each major phase.
6. Run the production build and tests.
7. Fix issues rather than merely reporting them.
8. Finish by documenting the implemented routes, features, run commands, test results and limitations.

Do not stop after creating the file structure. Do not leave core controls inert. Do not claim an integration works unless it has been tested. If time is constrained, prioritize the complete core journey—load portfolio, inspect exposure, run a stress scenario, inspect evidence—over decorative features.

**Expected final result:** a responsive, polished, working React frontend for Risvanta that can be demonstrated without a backend and is structured to connect to one later.
