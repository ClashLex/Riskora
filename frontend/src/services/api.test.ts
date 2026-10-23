import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

afterEach(() => vi.unstubAllGlobals())

const holding = { id: 'holding-1', name: 'Sample Asset', ticker: null, asset_class: 'stock', market_value: 2500, currency: 'USD', country: null, sector: 'Technology', quantity: null, source_label: 'Illustrative', source_id: 'src-demo', as_of_date: '2026-06-30', data_status: 'illustrative', is_demo: true }
const portfolio = { id: 'demo-global', name: 'Sample', base_currency: 'USD', holdings: [holding], total_value: 2500, value_complete: true, holding_valuations: [{ holding_id: 'holding-1', base_value: 2500, fx_rate: 1 }], warnings: [], is_demo: true }

describe('API contract', () => {
  it('reads backend portfolio fields instead of local fixture fields', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(portfolio), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    const response = await api.portfolio('demo-global')
    expect(response.holdings[0].market_value).toBe(2500)
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/portfolios/demo-global')
  })
  it('sends snake_case holding payloads, handles DELETE 204 and preserves errors', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(portfolio), { status: 201 })).mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: 'No such portfolio' } }), { status: 404 }))
    vi.stubGlobal('fetch', fetch)
    await api.addHolding('demo-global', { name: 'Sample Asset', market_value: 2500, currency: 'USD', asset_class: 'stock', as_of_date: '2026-06-30' })
    expect(JSON.parse(fetch.mock.calls[0][1].body).market_value).toBe(2500)
    await expect(api.deleteHolding('demo-global','holding-1')).resolves.toBeUndefined()
    await expect(api.portfolio('missing')).rejects.toMatchObject({ message: 'No such portfolio', status: 404 })
  })
  it('rejects malformed responses rather than substituting demo values', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...portfolio, total_value: 'invalid' }), { status: 200 })))
    await expect(api.portfolio('demo-global')).rejects.toBeInstanceOf(ApiError)
  })
  it('keeps incomplete scenario totals null', async () => {
    const incomplete = { result_id: 'result-1', scenario_id: 'custom', base_currency: 'USD', portfolio_value_before: 2500, portfolio_value_after: null, estimated_change: null, modeled_estimated_change: -100, estimated_change_percent: null, is_complete: false, is_simulation: true, data_status: 'illustrative', as_of_date: '2026-06-30', assumptions: [], limitations: ['Unmapped'], rows: [{ id:'position-1', name:'Sample Asset', exposure_base_value:2500, asset_return:null, fx_return:null, estimated_change_base_value:null, post_shock_base_value:null, data_status:'not_modelled', is_modelled:false, holding_ids:['holding-1'], source_ids:['src-demo'], as_of_date:'2026-06-30', explanation:'Missing sector mapping' }], source_ids:[], sources:[], warnings:[] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(incomplete), { status: 200 })))
    const response = await api.run('demo-global', { scenario_id: 'custom', base_currency: 'USD' })
    expect(response.estimated_change).toBeNull()
    expect(response.rows[0].is_modelled).toBe(false)
  })
})
