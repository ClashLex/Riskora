import { z } from 'zod'
import { currencies } from '../data'
import type { Currency } from '../types'

export const useMockData = import.meta.env.VITE_USE_MOCK_DATA !== 'false'
const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const currency = z.enum(currencies)
const status = z.enum(['illustrative', 'user_entered', 'verified_source', 'delayed', 'not_modelled'])
const holding = z.object({ id: z.string(), name: z.string(), ticker: z.string().nullable(), asset_class: z.enum(['stock', 'etf', 'mutual_fund', 'bond', 'cash', 'other']), market_value: z.coerce.number(), currency, country: z.string().nullable(), sector: z.string().nullable(), quantity: z.coerce.number().nullable(), source_label: z.string(), source_id: z.string(), as_of_date: z.string(), data_status: status, is_demo: z.boolean() })
const source = z.object({ id: z.string(), name: z.string(), source_url: z.string().nullable(), as_of_date: z.string(), data_status: status })
export const portfolioSchema = z.object({ id: z.string(), name: z.string(), base_currency: currency, holdings: z.array(holding), total_value: z.number(), value_complete: z.boolean(), holding_valuations: z.array(z.object({ holding_id: z.string(), base_value: z.number().nullable(), fx_rate: z.number().nullable() })), warnings: z.array(z.string()), is_demo: z.boolean() })
export const summarySchema = z.array(z.object({ id: z.string(), name: z.string(), base_currency: currency, total_value: z.number(), value_complete: z.boolean(), holding_count: z.number(), is_demo: z.boolean() }))
const contribution = z.object({ id: z.string(), name: z.string(), value: z.number(), holding_ids: z.array(z.string()), is_fund_derived: z.boolean(), data_status: z.string(), source_ids: z.array(z.string()), as_of_date: z.string() })
const group = z.object({ key: z.string(), value: z.number(), percent: z.number(), contributions: z.array(contribution), source_ids: z.array(z.string()), as_of_dates: z.array(z.string()), data_statuses: z.array(z.string()) })
export const exposureSchema = z.object({ portfolio_id: z.string(), base_currency: currency, total_portfolio_value: z.number(), value_complete: z.boolean(), coverage_percent: z.number(), groups: z.record(z.string(), z.array(group)), overlaps: z.array(z.object({ underlying_asset_id: z.string(), name: z.string(), total_exposure: z.number(), direct_exposure: z.number(), fund_derived_exposure: z.number(), fund_count: z.number(), direct_holding_count: z.number(), holding_ids: z.array(z.string()), source_ids: z.array(z.string()) })), fund_coverage: z.array(z.object({ holding_id: z.string(), coverage_percent: z.number(), covered_value: z.number(), uncovered_percent: z.number() })), sources: z.array(source), warnings: z.array(z.string()), as_of_dates: z.array(z.string()), unmapped_holding_ids: z.array(z.string()), unconverted_holding_ids: z.array(z.string()) })
export const insightSchema = z.array(z.object({ id: z.string(), title: z.string(), severity: z.string(), explanation: z.string(), calculation_details: z.record(z.string(), z.unknown()), related_holding_ids: z.array(z.string()), source_ids: z.array(z.string()), data_status: z.string(), as_of_date: z.string(), limitations: z.array(z.string()) }))
export const scenarioDefinitionSchema = z.array(z.object({ id: z.string(), name: z.string(), description: z.string(), default_asset_shock_percent: z.number(), default_fx_shock_percent: z.number(), method: z.string(), limitations: z.array(z.string()), data_status: z.string() }))
export const scenarioResultSchema = z.object({ result_id: z.string(), scenario_id: z.string(), base_currency: currency, portfolio_value_before: z.number(), portfolio_value_after: z.number().nullable(), estimated_change: z.number().nullable(), modeled_estimated_change: z.number(), estimated_change_percent: z.number().nullable(), is_complete: z.boolean(), is_simulation: z.boolean(), data_status: z.string(), as_of_date: z.string(), assumptions: z.array(z.string()), limitations: z.array(z.string()), rows: z.array(z.object({ id: z.string(), name: z.string(), exposure_base_value: z.number(), asset_return: z.number().nullable(), fx_return: z.number().nullable(), estimated_change_base_value: z.number().nullable(), post_shock_base_value: z.number().nullable(), data_status: z.string(), is_modelled: z.boolean(), holding_ids: z.array(z.string()), source_ids: z.array(z.string()), as_of_date: z.string(), explanation: z.string() })), source_ids: z.array(z.string()), sources: z.array(source), warnings: z.array(z.string()) })
export const explanationSchema = z.object({ result_id: z.string(), explanation: z.string(), mode: z.string(), source_ids: z.array(z.string()), data_status: z.string(), as_of_date: z.string() })

export type ApiHolding = z.infer<typeof holding>
export type ApiPortfolio = z.infer<typeof portfolioSchema>
export type ApiSummary = z.infer<typeof summarySchema>[number]
export type ApiExposure = z.infer<typeof exposureSchema>
export type ApiInsight = z.infer<typeof insightSchema>[number]
export type ApiScenario = z.infer<typeof scenarioDefinitionSchema>[number]
export type ApiResult = z.infer<typeof scenarioResultSchema>

export class ApiError extends Error { status?: number; constructor(message: string, status?: number) { super(message); this.status = status } }
async function request<T>(path: string, schema: z.ZodType<T>, method = 'GET', body?: unknown): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 10000)
  try {
    const response = await fetch(`${baseUrl}${path}`, { method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal })
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null)
      const parsed = z.object({ error: z.object({ message: z.string() }) }).safeParse(payload)
      throw new ApiError(parsed.success ? parsed.data.error.message : `Analysis service returned HTTP ${response.status}.`, response.status)
    }
    if (response.status === 204) return undefined as T
    const parsed = schema.safeParse(await response.json())
    if (!parsed.success) throw new ApiError('The analysis service returned an unexpected response.')
    return parsed.data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError('The analysis service timed out. Please retry.')
    throw new ApiError('We couldn’t connect to the analysis service. Check that the backend is running.')
  } finally { clearTimeout(timer) }
}

const route = (id: string) => `/portfolios/${encodeURIComponent(id)}`
export const api = {
  portfolios: () => request('/portfolios', summarySchema),
  portfolio: (id: string) => request(route(id), portfolioSchema),
  createPortfolio: (name: string, base_currency: Currency) => request('/portfolios', portfolioSchema, 'POST', { name, base_currency }),
  addHolding: (id: string, holding: Record<string, unknown>) => request(`${route(id)}/holdings`, portfolioSchema, 'POST', holding),
  updateHolding: (id: string, holdingId: string, patch: Record<string, unknown>) => request(`${route(id)}/holdings/${encodeURIComponent(holdingId)}`, portfolioSchema, 'PATCH', patch),
  deleteHolding: (id: string, holdingId: string) => request(`${route(id)}/holdings/${encodeURIComponent(holdingId)}`, z.void(), 'DELETE'),
  resetDemo: (id: string) => request(`${route(id)}/load-demo`, portfolioSchema, 'POST'),
  exposure: (id: string, base: Currency) => request(`${route(id)}/exposure?base_currency=${base}`, exposureSchema),
  insights: (id: string, base: Currency) => request(`${route(id)}/insights?base_currency=${base}`, insightSchema),
  scenarios: () => request('/scenarios', scenarioDefinitionSchema),
  run: (id: string, data: Record<string, unknown>) => request(`${route(id)}/scenarios/run`, scenarioResultSchema, 'POST', data),
  explain: (id: string, result_id: string, question: string) => request(`${route(id)}/explanations`, explanationSchema, 'POST', { result_id, question }),
}
