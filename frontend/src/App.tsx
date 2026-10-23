import { useState } from 'react'
import type { FormEvent, ChangeEvent } from 'react'
import { Activity, ArrowDownRight, ArrowUpRight, FileUp, Info, RotateCcw, ShieldCheck, Upload } from 'lucide-react'

type Allocation = Record<string, number>
type Analysis = {
  totalValueInr: number
  allocations: {
    sectors: Allocation
    currencies: Allocation
    assetClasses: Allocation
  }
  overlaps: {
    symbol: string
    funds: { scheme: string; weight: number }[]
    totalOverlapPercent: number
    sources: string[]
  }[]
  stressResults: {
    marketShockPnl: number
    fxShockPnl: number
    totalPnl: number
    newPortfolioValue: number
    equityShockPercent: number
    usdInrChange: number
    usdInrRate: number
  }
  riskMetrics: {
    issuerConcentrationHhi: number
    topExposures: { symbol: string; valueInr: number; weight: number }[]
    equityValueInr: number
    usdExposureInr: number
  }
  explanation: string
  sources: { name: string; url: string }[]
  dataNotes: string[]
  disclaimer: string
}

const demoPortfolio = [
  {
    type: 'equity',
    symbol: 'TCS',
    quantity: 10,
    price: 3500,
    currency: 'INR',
    sector: 'Information Technology',
  },
  {
    type: 'mf',
    symbol: 'Sample Large Cap Fund',
    quantity: 200,
    price: 50,
    amc: 'Illustrative AMC',
    constituents: [
      { symbol: 'RELIANCE', weight: 0.12, sector: 'Energy', currency: 'INR' },
      { symbol: 'TCS', weight: 0.25, sector: 'Information Technology', currency: 'INR' },
      { symbol: 'HDFC Bank', weight: 0.18, sector: 'Banking', currency: 'INR' },
    ],
  },
  {
    type: 'mf',
    symbol: 'Sample Flexi Cap Fund',
    quantity: 100,
    price: 100,
    amc: 'Illustrative AMC',
    constituents: [
      { symbol: 'RELIANCE', weight: 0.1, sector: 'Energy', currency: 'INR' },
      { symbol: 'TCS', weight: 0.15, sector: 'Information Technology', currency: 'INR' },
      { symbol: 'ICICI Bank', weight: 0.2, sector: 'Banking', currency: 'INR' },
    ],
  },
  {
    type: 'us_stock',
    symbol: 'AAPL',
    quantity: 3,
    price: 210,
    currency: 'USD',
    sector: 'Technology',
  },
]

const moneyInr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const percent = new Intl.NumberFormat('en-IN', { style: 'percent', maximumFractionDigits: 1 })

async function analyze(body: unknown): Promise<Analysis> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as {
      detail?: string | { loc?: string[]; msg?: string }[]
    }
    const detail = payload.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => `${item.loc?.slice(-1)[0] ?? 'Input'}: ${item.msg ?? 'Invalid value'}`).join('; ')
        : `Analysis failed (${response.status})`
    throw new Error(message)
  }
  return response.json() as Promise<Analysis>
}

function AllocationBars({ title, values }: { title: string; values: Allocation }) {
  const entries = Object.entries(values).sort((first, second) => second[1] - first[1])
  return <section className="panel allocation-panel">
    <div className="panel-title"><h2>{title}</h2><span>Share of portfolio</span></div>
    {entries.map(([label, value], index) => <div className="allocation-row" key={label}>
      <div className="allocation-label"><span>{label}</span><strong>{percent.format(value)}</strong></div>
      <div className="allocation-track"><span style={{ width: `${Math.max(value * 100, 1)}%` }} className={`allocation-fill color-${index % 5}`}/></div>
    </div>)}
  </section>
}

function App() {
  const [portfolioText, setPortfolioText] = useState('')
  const [equityShock, setEquityShock] = useState(-10)
  const [fxShock, setFxShock] = useState(5)
  const [fxRate, setFxRate] = useState('83.5')
  const [result, setResult] = useState<Analysis | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [demoLoaded, setDemoLoaded] = useState(false)

  function loadDemo() {
    setPortfolioText(JSON.stringify(demoPortfolio, null, 2))
    setDemoLoaded(true)
    setResult(null)
    setError('')
  }

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      setPortfolioText(await file.text())
      setDemoLoaded(false)
      setResult(null)
      setError('')
    } catch {
      setError('Could not read that file. Choose a valid JSON portfolio file.')
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const portfolio = JSON.parse(portfolioText) as unknown
      if (!Array.isArray(portfolio)) {
        throw new Error('Portfolio JSON must be an array of holdings.')
      }
      const rate = Number(fxRate)
      if (!Number.isFinite(rate) || rate <= 0) {
        throw new Error('Enter a positive INR-per-USD exchange rate.')
      }
      setResult(await analyze({
        portfolio,
        scenario: { equityShockPercent: equityShock, usdInrChange: fxShock },
        usd_inr_rate: rate,
      }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to analyze this portfolio.')
    } finally {
      setBusy(false)
    }
  }

  function clearPortfolio() {
    setPortfolioText('')
    setResult(null)
    setError('')
    setDemoLoaded(false)
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#top" aria-label="Portfolio Lens home">
        <span className="brand-mark"><Activity size={19}/></span>
        <span><strong>PORTFOLIO LENS</strong><small>RISK WORKSPACE</small></span>
      </a>
      <div className="sidebar-section">ANALYSIS</div>
      <div className="side-current"><span className="side-icon">01</span><span>Portfolio risk</span><i/></div>
      <div className="privacy-card"><ShieldCheck size={17}/><div><strong>Private by design</strong><p>Analysis is performed per request. Portfolio data is not stored.</p></div></div>
      <div className="sidebar-bottom"><div className="profile-dot">PL</div><div><strong>Local analysis</strong><small>No account required</small></div></div>
    </aside>
    <main className="main-area" id="top">
      <header className="topbar"><div><span>WORKSPACE</span><b>/</b><strong>Portfolio risk</strong></div><span className="local-badge"><i/> LOCAL & PRIVATE</span></header>
      <div className="content">
        <section className="hero">
          <div><div className="eyebrow">PORTFOLIO RISK ANALYSIS</div><h1>See what your portfolio is really exposed to.</h1>
            <p>Look through your mutual funds, understand concentration, and test how a market or currency shock could affect your portfolio value in rupees.</p></div>
          <div className="hero-mark"><Activity size={27}/><span>DETERMINISTIC<br/>RISK ENGINE</span></div>
        </section>

        {error && <div className="alert error" role="alert"><Info size={17}/><span>{error}</span></div>}

        <form className="workspace-grid" onSubmit={(event) => void submit(event)}>
          <section className="panel input-panel">
            <div className="panel-heading"><div><span className="step">01</span><div><h2>Your holdings</h2><p>Enter holdings as JSON or upload a JSON file.</p></div></div>
              <div className="button-row">
                <label className="button secondary file-button"><FileUp size={15}/>Upload JSON<input type="file" accept=".json,application/json" onChange={(event) => void loadFile(event)}/></label>
                <button type="button" className="button secondary" onClick={loadDemo}><RotateCcw size={14}/>Load demo</button>
              </div>
            </div>
            <textarea aria-label="Portfolio holdings JSON" spellCheck={false} value={portfolioText} onChange={(event) => { setPortfolioText(event.target.value); setDemoLoaded(false) }} placeholder={'[\n  {\n    "type": "equity",\n    "symbol": "TCS",\n    "quantity": 10,\n    "price": 3000,\n    "currency": "INR",\n    "sector": "Information Technology"\n  }\n]'} required/>
            {demoLoaded && <div className="demo-note">Illustrative sample prices and fund constituents only — not live or actual fund data.</div>}
            <div className="format-note"><Info size={14}/><span>Supported types: <code>equity</code>, <code>mf</code>, <code>us_stock</code>, <code>etf</code>, <code>debt</code>. Add mutual-fund constituents with fractional weights to enable look-through.</span></div>
            <button type="button" className="clear-button" onClick={clearPortfolio}>Clear portfolio</button>
          </section>

          <section className="panel scenario-panel">
            <div className="panel-heading"><div><span className="step">02</span><div><h2>Stress scenario</h2><p>Apply linear shocks to your supplied values.</p></div></div></div>
            <label className="range-label" htmlFor="equity-shock"><span>Equity market move</span><strong>{equityShock > 0 ? '+' : ''}{equityShock}%</strong></label>
            <input id="equity-shock" type="range" min="-50" max="30" step="1" value={equityShock} onChange={(event) => setEquityShock(Number(event.target.value))}/>
            <div className="range-ends"><span>-50%</span><span>+30%</span></div>
            <label className="range-label" htmlFor="fx-shock"><span>USD/INR move</span><strong>{fxShock > 0 ? '+' : ''}{fxShock}%</strong></label>
            <input id="fx-shock" type="range" min="-20" max="20" step="1" value={fxShock} onChange={(event) => setFxShock(Number(event.target.value))}/>
            <div className="range-ends"><span>-20%</span><span>+20%</span></div>
            <label className="rate-label" htmlFor="fx-rate">INR per USD <span>User supplied — no live FX feed</span></label>
            <input id="fx-rate" type="number" min="0.01" step="0.01" value={fxRate} onChange={(event) => setFxRate(event.target.value)}/>
            <button className="button primary analyze-button" type="submit" disabled={busy || !portfolioText.trim()}><Activity size={16}/>{busy ? 'Analyzing…' : 'Analyze portfolio'}</button>
          </section>
        </form>

        {result ? <section className="results" aria-live="polite">
          <div className="results-heading"><div><div className="eyebrow">YOUR ANALYSIS</div><h2>Portfolio risk overview</h2></div><span className="result-value">{moneyInr.format(result.totalValueInr)}<small>Current supplied value</small></span></div>
          <div className="metrics">
            <article className="metric"><span>Scenario portfolio value</span><strong>{moneyInr.format(result.stressResults.newPortfolioValue)}</strong><small>After selected market and FX shocks</small></article>
            <article className="metric"><span>Estimated scenario change</span><strong className={result.stressResults.totalPnl >= 0 ? 'positive' : 'negative'}>{result.stressResults.totalPnl >= 0 ? <ArrowUpRight size={17}/> : <ArrowDownRight size={17}/>} {moneyInr.format(result.stressResults.totalPnl)}</strong><small>Linear illustrative estimate</small></article>
            <article className="metric"><span>Largest single exposure</span><strong>{result.riskMetrics.topExposures[0] ? percent.format(result.riskMetrics.topExposures[0].weight) : '—'}</strong><small>{result.riskMetrics.topExposures[0]?.symbol ?? 'No exposure available'}</small></article>
            <article className="metric"><span>Mutual-fund overlaps</span><strong>{result.overlaps.length}</strong><small>Shared constituent entries found</small></article>
          </div>
          <div className="allocation-grid">
            <AllocationBars title="Sector exposure" values={result.allocations.sectors}/>
            <AllocationBars title="Asset class exposure" values={result.allocations.assetClasses}/>
            <AllocationBars title="Currency exposure" values={result.allocations.currencies}/>
          </div>
          <div className="detail-grid">
            <section className="panel overlap-panel">
              <div className="panel-title"><div><h2>Mutual-fund overlap</h2><span>Shared securities based only on supplied constituent lists.</span></div></div>
              {result.overlaps.length ? <div className="overlap-list">{result.overlaps.map((overlap) => <article className="overlap-row" key={overlap.symbol}>
                <div><strong>{overlap.symbol}</strong><small>{overlap.funds.map((fund) => fund.scheme).join(' · ')}</small></div>
                <div className="overlap-value">{overlap.totalOverlapPercent.toFixed(2)}%<small>of portfolio</small></div>
                <div className="fund-contributions">{overlap.funds.map((fund) => <span key={fund.scheme}>{fund.scheme}: {percent.format(fund.weight)}</span>)}</div>
                {overlap.sources.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>)}
              </article>)}</div> : <div className="empty-state">No shared constituents were found across the provided mutual funds. Missing constituent data means overlap cannot be assessed.</div>}
            </section>
            <section className="panel stress-panel">
              <div className="panel-title"><div><h2>Scenario impact</h2><span>Separate linear equity and currency effects.</span></div></div>
              <div className="impact-row"><span>Equity shock ({result.stressResults.equityShockPercent}%)</span><strong className={result.stressResults.marketShockPnl >= 0 ? 'positive' : 'negative'}>{moneyInr.format(result.stressResults.marketShockPnl)}</strong></div>
              <div className="impact-row"><span>USD/INR shock ({result.stressResults.usdInrChange}%)</span><strong className={result.stressResults.fxShockPnl >= 0 ? 'positive' : 'negative'}>{moneyInr.format(result.stressResults.fxShockPnl)}</strong></div>
              <div className="impact-total"><span>Estimated combined change</span><strong>{moneyInr.format(result.stressResults.totalPnl)}</strong></div>
              <div className="impact-note">USD/INR rate used: ₹{result.stressResults.usdInrRate.toFixed(4)} per USD. A stronger USD increases INR value of unchanged USD holdings in this model.</div>
            </section>
          </div>
          <section className="panel explanation-panel">
            <div className="panel-title"><div><h2>What stands out</h2><span>Transparent, formula-based explanation of the returned metrics.</span></div></div>
            <p>{result.explanation}</p>
            {result.sources.length > 0 && <div className="source-list"><strong>Input sources provided</strong>{result.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.name} <span>{source.url}</span></a>)}</div>}
            <ul className="data-notes">{result.dataNotes.map((note) => <li key={note}>{note}</li>)}</ul>
          </section>
          <div className="disclaimer"><Info size={16}/><span>{result.disclaimer}</span></div>
        </section> : <section className="empty-results"><span><Upload size={20}/></span><div><h2>Your analysis will appear here</h2><p>Enter your holdings, set a scenario, and run the deterministic portfolio risk analysis.</p></div></section>}

        <footer><span>PORTFOLIO LENS</span><span>Educational analysis only · Not investment advice · No trades are placed</span></footer>
      </div>
    </main>
  </div>
}

export default App
