// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { api } from './api'
import { DataTable } from './components/ui'
import PillNav from './components/PillNav'
import { useResearch } from './hooks/useResearch'
import { useResource } from './hooks/useResource'

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
      eligible_funds: 0,
      latest_real_report: null,
      latest_update: null,
      training_status: 'not_trained',
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
  const tokenField = screen.getByLabelText('Management token') as HTMLInputElement
  expect(tokenField.type).toBe('password')
  await user.click(screen.getByRole('button', { name: 'Show management token' }))
  expect(tokenField.type).toBe('text')
  await user.click(screen.getByRole('button', { name: 'Hide management token' }))
  expect(tokenField.type).toBe('password')
  const nav = screen.getByRole('navigation', { name: 'Main navigation' })
  const menu = within(nav).queryByRole('button', { name: 'Open menu' })
  if (menu) await user.click(menu)
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
  expect(await screen.findByRole('region', { name: 'Disclosure coverage' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Data checks' })).toBeTruthy()
  expect(screen.getByText('No historical holdings imported.')).toBeTruthy()
  expect(screen.queryByText('Proof')).toBeNull()
})

it('explains why supporting signals are empty when no funds are loaded', async () => {
  vi.mocked(fetch).mockImplementation(async (input) =>
    response(String(input).endsWith('/funds') ? [] : fixture(String(input))),
  )
  window.history.replaceState(null, '', '/#evidence')
  render(<App />)

  expect(await screen.findByRole('heading', { name: 'No supporting signals yet' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Manage data' })).toBeTruthy()

  act(() => {
    window.history.replaceState(null, '', '/#predictions')
    window.dispatchEvent(new Event('hashchange'))
  })
  expect(await screen.findByRole('heading', { name: 'No fund data to rank' })).toBeTruthy()
})

it('closes the mobile menu when navigation expands and does not reopen it on collapse', async () => {
  const user = userEvent.setup()
  const items = [{ label: 'Overview', href: '#overview' }]
  const { rerender } = render(<PillNav items={items} collapse="always" intro={false} />)

  await user.click(screen.getByRole('button', { name: 'Open menu' }))
  expect(screen.getByRole('button', { name: 'Close menu' }).getAttribute('aria-expanded')).toBe(
    'true',
  )

  await user.click(screen.getByRole('button', { name: 'Close menu' }))
  expect(screen.queryByRole('link', { name: 'Overview' })).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Open menu' }))

  rerender(<PillNav items={items} collapse="never" intro={false} />)
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Close menu' })).toBeNull())

  rerender(<PillNav items={items} collapse="always" intro={false} />)
  expect(screen.getByRole('button', { name: 'Open menu' }).getAttribute('aria-expanded')).toBe(
    'false',
  )
})

it('shows coverage on Overview and keeps the fund library in Fund explorer', async () => {
  const user = userEvent.setup()
  vi.mocked(fetch).mockImplementation(async (input) =>
    response(
      String(input).endsWith('/overview')
        ? {
            funds: 2,
            observations: 25,
            securities: 10,
            eligible_funds: 2,
            imported_observations: 10,
            synthetic_observations: 15,
            latest_real_report: '2024-03-31',
            latest_update: '2024-04-08T00:00:00Z',
            training_status: 'ready',
            warnings: [],
          }
        : fixture(String(input)),
    ),
  )
  render(<App />)
  const coverage = await screen.findByRole('region', { name: 'Disclosure coverage' })
  expect(within(coverage).getByText('Imported disclosures')).toBeTruthy()
  expect(within(coverage).getByText('10')).toBeTruthy()
  expect(within(coverage).getByText('Sample disclosures')).toBeTruthy()
  expect(within(coverage).getByText('15')).toBeTruthy()
  expect(screen.queryByRole('table')).toBeNull()
  expect(screen.queryByRole('region', { name: 'Recent funds' })).toBeNull()
  expect(screen.queryByRole('complementary', { name: 'Fund library' })).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Explore funds' }))
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Fund disclosures')
  expect(screen.getByRole('complementary', { name: 'Fund library' })).toBeTruthy()
})

it('shows the fund library only in the explorer and filters its funds', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', '/#fund-explorer')
  render(<App />)
  const library = screen.getByRole('complementary', { name: 'Fund library' })
  await within(library).findByRole('button', { name: /Imported Fund/ })
  await user.type(within(library).getByRole('searchbox', { name: 'Find a fund' }), 'sample')
  expect(within(library).queryByRole('button', { name: /Imported Fund/ })).toBeNull()
  const sample = within(library).getByRole('button', { name: /Sample Fund/ })
  await user.click(sample)
  expect(sample.getAttribute('aria-pressed')).toBe('true')
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Fund disclosures')
  window.history.pushState(null, '', '#overview')
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(screen.queryByRole('complementary', { name: 'Fund library' })).toBeNull()
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

it('shows complete records and usable sorting on narrow screens', async () => {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  )
  const user = userEvent.setup()
  render(
    <DataTable
      caption="Fund coverage"
      rows={[
        { id: 'z', name: 'Zebra Fund', count: 3 },
        { id: 'a', name: 'Alpha Fund', count: 9 },
      ]}
      rowKey={(row) => row.id}
      search={(row) => row.name}
      columns={[
        { key: 'name', label: 'Fund', render: (row) => row.name, sort: (row) => row.name },
        {
          key: 'count',
          label: 'Disclosures',
          render: (row) => row.count,
          sort: (row) => row.count,
        },
      ]}
    />,
  )
  expect(screen.queryByRole('table')).toBeNull()
  const records = screen.getByRole('list', { name: 'Fund coverage' })
  expect(within(records).getAllByRole('listitem')[0].textContent).toContain('Zebra Fund')
  expect(within(records).getAllByRole('listitem')[0].textContent).toContain('Disclosures3')
  expect(screen.queryByRole('button', { name: 'Sort descending' })).toBeNull()
  await user.selectOptions(screen.getByLabelText('Sort fund coverage'), 'name')
  expect(within(records).getAllByRole('listitem')[0].textContent).toContain('Alpha Fund')
  await user.click(screen.getByRole('button', { name: 'Sort descending' }))
  expect(within(records).getAllByRole('listitem')[0].textContent).toContain('Zebra Fund')
  await user.type(screen.getByRole('searchbox', { name: 'Search fund coverage' }), 'alpha')
  expect(within(records).getAllByRole('listitem')).toHaveLength(1)
  expect(within(records).getByText('Alpha Fund')).toBeTruthy()
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
