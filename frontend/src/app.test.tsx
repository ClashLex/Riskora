// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const analysis = {
  totalValueInr: 100000,
  allocations: {
    sectors: { IT: 0.4, Others: 0.6 },
    currencies: { INR: 1 },
    assetClasses: { Equity: 0.4, Other: 0.6 },
  },
  overlaps: [],
  stressResults: {
    marketShockPnl: -4000,
    fxShockPnl: 0,
    totalPnl: -4000,
    newPortfolioValue: 96000,
    equityShockPercent: -10,
    usdInrChange: 5,
    usdInrRate: 83.5,
  },
  riskMetrics: {
    issuerConcentrationHhi: 0.52,
    topExposures: [{ symbol: 'TCS', valueInr: 40000, weight: 0.4 }],
    equityValueInr: 40000,
    usdExposureInr: 0,
  },
  explanation: 'The supplied portfolio has a 40% IT exposure.',
  sources: [],
  dataNotes: ['Portfolio data is not persisted.'],
  disclaimer: 'For educational analysis only. Not investment advice.',
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(analysis), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('portfolio risk workspace', () => {
  it('renders the portfolio analyzer and privacy notice', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'See what your portfolio is really exposed to.' })).toBeTruthy()
    expect(screen.getByText('Private by design')).toBeTruthy()
    expect(screen.getByText('Not investment advice', { exact: false })).toBeTruthy()
  })

  it('loads illustrative holdings and submits a stress analysis', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Load demo' }))
    expect(screen.getByText(/Illustrative sample prices and fund constituents only/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Analyze portfolio' }))

    expect(await screen.findByRole('heading', { name: 'Portfolio risk overview' })).toBeTruthy()
    expect(screen.getByText(/Illustrative sample prices and fund constituents only/)).toBeTruthy()
    expect(screen.getByText('₹96,000')).toBeTruthy()
    expect(screen.getByText('The supplied portfolio has a 40% IT exposure.')).toBeTruthy()
    const [url, request] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('/api/analyze')
    expect(JSON.parse(String(request?.body)).portfolio).toHaveLength(4)
  })

  it('shows a clear validation error for malformed portfolio JSON', async () => {
    const user = userEvent.setup()
    render(<App />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Portfolio holdings JSON' }), {
      target: { value: '{bad json' },
    })
    await user.click(screen.getByRole('button', { name: 'Analyze portfolio' }))
    expect((await screen.findByRole('alert')).textContent).toMatch(/JSON/)
  })
})
