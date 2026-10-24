// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { api } from './api'
import { useResearch } from './hooks/useResearch'
import { useResource } from './hooks/useResource'

// jsdom does not implement native dialog methods; browser checks cover focus trapping.
Object.defineProperties(HTMLDialogElement.prototype, {
  showModal: {
    configurable: true,
    writable: true,
    value() {
      this.open = true
    },
  },
  close: {
    configurable: true,
    writable: true,
    value() {
      this.open = false
    },
  },
})

const funds = [
  {
    id: 'imported',
    name: 'Imported Fund',
    amc: 'Imported AMC',
    source_kind: 'user_import',
    observations: 10,
    latest_report_date: '2024-03-31',
  },
  {
    id: 'sample',
    name: 'Sample Fund',
    amc: 'Sample AMC',
    source_kind: 'synthetic',
    observations: 15,
    latest_report_date: '2024-03-31',
  },
]
const runs = [
  {
    id: 2,
    source_kind: 'synthetic',
    horizon: 'month',
    status: 'complete',
    model_version: 'logistic-v2',
    current_method: true,
    metrics: {},
  },
  {
    id: 1,
    source_kind: 'user_import',
    horizon: 'month',
    status: 'complete',
    model_version: 'logistic-v2',
    current_method: true,
    metrics: {},
  },
]
const candidates = [
  {
    isin: 'IN0000000001',
    company: 'Zebra Industries',
    sector: 'Industrials',
    score: 0.8,
    features: { market_available: 0 },
    contributions: {},
    evidence: [],
  },
  {
    isin: 'IN0000000002',
    company: 'Alpha Bank',
    sector: 'Banks',
    score: 0.3,
    features: { market_available: 1 },
    contributions: {},
    evidence: [],
  },
]
function prediction(id = 'imported') {
  return {
    scheme_id: id,
    cutoff: '2024-04-08',
    observation_date: '2024-03-31',
    published_at: '2024-04-08',
    generated_at: '2026-10-24T10:00:00Z',
    horizon: 'month',
    run_id: 1,
    model_version: 'logistic-v2',
    materiality: 0.1,
    source_kind: id === 'sample' ? 'synthetic' : 'user_import',
    warning: 'Scores are not probabilities.',
    candidates,
  }
}
function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
function fixture(path: string) {
  if (path.endsWith('/overview'))
    return {
      funds: 0,
      warnings: ['No historical holdings imported.'],
      imported_observations: 0,
      synthetic_observations: 0,
    }
  if (path.endsWith('/funds')) return funds
  if (path.includes('/funds/'))
    return { scheme: funds.find((fund) => path.endsWith(fund.id)), snapshots: [], changes: [] }
  if (path.includes('/training-runs')) return runs
  if (path.includes('/readiness'))
    return {
      usable_periods: 0,
      label_counts: {},
      ready: false,
      blockers: [],
      requirements: 'Four comparable cutoff periods.',
    }
  if (path.includes('/predictions/')) return prediction(path.split('/').pop())
  if (path.includes('/evidence/')) return { holdings: [], market: [], events: [] }
  return []
}
beforeEach(() => {
  window.history.replaceState(null, '', '/')
  vi.stubGlobal('scrollTo', vi.fn())
  vi.spyOn(HTMLDialogElement.prototype, 'showModal').mockImplementation(function (
    this: HTMLDialogElement,
  ) {
    this.open = true
  })
  vi.spyOn(HTMLDialogElement.prototype, 'close').mockImplementation(function (
    this: HTMLDialogElement,
  ) {
    this.open = false
    this.dispatchEvent(new Event('close'))
  })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string) => response(fixture(String(input)))),
  )
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

it('keeps semantic navigation, direct links, and management access usable', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', '/#data-management')
  render(<App />)
  expect(await screen.findByRole('heading', { name: 'Manage data' })).toBeTruthy()
  const nav = screen.getByRole('navigation', { name: 'Main navigation' })
  expect(within(nav).getAllByRole('link')).toHaveLength(6)
  expect(screen.getByRole('link', { name: 'Data management' }).getAttribute('aria-current')).toBe(
    'page',
  )
  expect(
    screen.getByRole('button', { name: 'Load synthetic sample' }).hasAttribute('disabled'),
  ).toBe(true)
  const link = screen.getByRole('link', { name: 'Overview' })
  link.focus()
  await user.keyboard('{Enter}')
  expect(window.location.hash).toBe('#overview')
  expect(
    await screen.findByRole('heading', { name: 'Start with a fund’s disclosure history' }),
  ).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'Data checks' })).toBeNull()
  expect(screen.queryByText('Proof')).toBeNull()
})

it('filters the fund library and restores focus when the drawer closes', async () => {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByText('Imported Fund')
  await user.type(screen.getByRole('searchbox', { name: 'Find a fund' }), 'sample')
  expect(screen.queryByText('Imported Fund')).toBeNull()
  await user.click(screen.getByRole('button', { name: /Sample Fund/ }))
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Fund disclosures')
  const toggle = screen.getByRole('button', { name: 'Open fund library' })
  await user.click(toggle)
  expect(screen.getByRole('dialog', { name: 'Fund library' })).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Close fund library' }))
  expect(toggle.getAttribute('aria-expanded')).toBe('false')
  expect(document.activeElement).toBe(toggle)
})

it('selects evaluation runs by dataset and horizon and never fetches the global latest run', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', '/#evaluation')
  render(<App />)
  await waitFor(() =>
    expect((screen.getByLabelText('Evaluation run') as HTMLSelectElement).value).toBe('1'),
  )
  expect(
    vi.mocked(fetch).mock.calls.some(([path]) => String(path).endsWith('/backtests?run_id=1')),
  ).toBe(true)
  await user.selectOptions(screen.getByLabelText('Training dataset'), 'synthetic')
  await waitFor(() =>
    expect((screen.getByLabelText('Evaluation run') as HTMLSelectElement).value).toBe('2'),
  )
  await user.selectOptions(screen.getByLabelText('Prediction period'), 'quarter')
  expect(await screen.findByText('No evaluation for this selection')).toBeTruthy()
  expect(screen.queryByLabelText('Evaluation run')).toBeNull()
  expect(vi.mocked(fetch).mock.calls.some(([path]) => String(path).endsWith('/backtests'))).toBe(
    false,
  )
})

it('searches and sorts candidates while preserving original rank, then retries supporting signals', async () => {
  const user = userEvent.setup()
  let evidenceAttempts = 0
  vi.mocked(fetch).mockImplementation(async (input) => {
    if (String(input).includes('/evidence/') && evidenceAttempts++ === 0)
      return response({ detail: 'Source history temporarily unavailable.' }, 503)
    return response(fixture(String(input)))
  })
  window.history.replaceState(null, '', '/#predictions')
  render(<App />)
  const rank = screen.getByRole('button', { name: 'Rank candidates' })
  await waitFor(() => expect(rank.hasAttribute('disabled')).toBe(false))
  await user.click(rank)
  await screen.findByRole('table', { name: 'Ranked candidates' })
  await user.click(screen.getByRole('button', { name: 'Company' }))
  const table = screen.getByRole('table', { name: 'Ranked candidates' })
  expect(within(table).getAllByRole('row')[1].textContent).toContain('2Alpha Bank')
  expect(screen.getByRole('columnheader', { name: 'Company' }).getAttribute('aria-sort')).toBe(
    'ascending',
  )
  await user.type(screen.getByRole('searchbox', { name: 'Search ranked candidates' }), 'Zebra')
  expect(screen.queryByRole('button', { name: /Alpha Bank/ })).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Reset' }))
  await user.click(screen.getByRole('button', { name: /Alpha Bank: inspect/ }))
  expect(await screen.findByText('Source history temporarily unavailable.')).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Retry' }))
  expect(
    await screen.findByText('No company events available for this stock and cutoff.'),
  ).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Alpha Bank' })).toBeTruthy()
})

it('discards a ranking that finishes after the fund selection changes', async () => {
  let resolve: (response: Response) => void = () => {}
  vi.mocked(fetch).mockImplementation(async (input) =>
    String(input).includes('/predictions/')
      ? new Promise<Response>((done) => {
          resolve = done
        })
      : response(fixture(String(input))),
  )
  const { result } = renderHook(() => useResearch())
  await waitFor(() => expect(result.current.canRank).toBe(true))
  let request: Promise<void>
  act(() => {
    request = result.current.rank()
  })
  act(() => result.current.chooseFund('sample'))
  await act(async () => {
    resolve(response(prediction()))
    await request!
  })
  expect(result.current.fundId).toBe('sample')
  expect(result.current.prediction).toBeUndefined()
})

it('ignores late resource responses even when the transport does not honor abort', async () => {
  let resolve: (response: Response) => void = () => {}
  vi.mocked(fetch).mockImplementation(async (input) =>
    String(input).endsWith('/old')
      ? new Promise<Response>((done) => {
          resolve = done
        })
      : response({ name: 'Current fund' }),
  )
  const { result, rerender } = renderHook(({ path }) => useResource<{ name: string }>(path), {
    initialProps: { path: '/old' },
  })
  rerender({ path: '/new' })
  await waitFor(() => expect(result.current.data?.name).toBe('Current fund'))
  await act(async () => resolve(response({ name: 'Previous fund' })))
  expect(result.current.data?.name).toBe('Current fund')
})

it('shows offline errors and recovers on retry', async () => {
  vi.mocked(fetch).mockRejectedValue(new TypeError('Network failed'))
  const user = userEvent.setup()
  render(<App />)
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    expect.stringContaining('server could not be reached'),
  )
  vi.mocked(fetch).mockImplementation(async (input) => response(fixture(String(input))))
  await user.click(screen.getByRole('button', { name: 'Retry' }))
  expect(
    await screen.findByRole('heading', { name: 'Start with a fund’s disclosure history' }),
  ).toBeTruthy()
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
})

it('formats field validation errors and rejects unreadable successful responses', async () => {
  vi.mocked(fetch).mockResolvedValue(
    response({ detail: [{ loc: ['body', 'title'], msg: 'Must have at least 3 characters' }] }, 422),
  )
  await expect(api('/events')).rejects.toThrow('title: Must have at least 3 characters')
  vi.mocked(fetch).mockResolvedValue(new Response('<html>Wrong server</html>', { status: 200 }))
  await expect(api('/overview')).rejects.toThrow('unreadable response')
})
