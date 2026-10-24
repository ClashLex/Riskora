export type Page =
  'Overview' | 'Fund explorer' | 'Predictions' | 'Evidence' | 'Evaluation' | 'Data management'
export type Horizon = 'month' | 'quarter'
export type SourceKind = 'user_import' | 'synthetic'
export type Fund = {
  id: string
  name: string
  amc: string
  category: string | null
  source_kind: SourceKind
  observations: number
  latest_report_date: string | null
  latest_published_at: string | null
}
export type Holding = {
  isin: string
  company: string
  sector: string | null
  industry: string | null
  weight: number
  units: number | null
}
export type Snapshot = {
  id: number
  report_date: string
  published_at: string
  source_url: string
  complete: number
  weight_total: number
  warnings: string[]
  holdings: Holding[]
}
export type Change = {
  isin: string
  cutoff: string
  target_report_date: string
  label: string
  horizon: Horizon
}
export type FundDetail = {
  scheme: Fund
  snapshots: Snapshot[]
  changes: Change[]
  changes_total: number
}
export type Candidate = {
  isin: string
  company: string
  sector: string | null
  score: number
  features: Record<string, number | null>
  contributions: Record<string, number>
  evidence: {
    type: string
    date: string
    published_at?: string
    source_url: string
    note?: string
  }[]
}
export type Prediction = {
  scheme_id: string
  cutoff: string
  observation_date: string
  published_at: string
  generated_at: string
  horizon: Horizon
  run_id: number
  model_version: string
  materiality: number
  source_kind: SourceKind
  warning: string
  candidates: Candidate[]
}
export type Metrics = {
  cases?: number
  positives?: number
  precision_at_5?: number
  recall_at_5?: number | null
  average_precision?: number | null
  status?: string
  reason?: string
}
export type Run = {
  id: number
  source_kind: SourceKind
  horizon: Horizon
  status: string
  model_version: string
  current_method: boolean
  train_end: string
  test_start: string
  finished_at: string
  metrics: Record<string, Metrics> | null
}
export type Overview = {
  funds: number
  observations: number
  securities: number
  eligible_funds: number
  imported_observations: number
  synthetic_observations: number
  latest_real_report: string | null
  latest_update: string | null
  training_status: string
  warnings: string[]
}
export type Readiness = {
  label_counts: Record<string, number>
  usable_periods: number
  ready: boolean
  requirements: string
  blockers: string[]
}
export type Evidence = {
  holdings: { report_date: string; published_at: string; source_url: string; weight: number }[]
  market: { date: string; close: number; volume: number; source_url: string }[]
  events: { title: string; published_at: string; source_url: string; excerpt: string }[]
}
export type Backtest = {
  run_id: number
  phase: string
  period: string
  model: string
  metrics: Metrics
}
export type Identifier = {
  isin: string
  company: string
  ticker: string | null
  sector: string | null
  reviewed_at: string | null
}

export const sourceName = (source: string) =>
  source === 'synthetic' ? 'Synthetic sample' : 'Imported data'
export const periodName = (horizon: Horizon) => (horizon === 'month' ? 'Monthly' : 'Quarterly')
export function dateLabel(value?: string | null, includeTime = false) {
  if (!value) return 'Unavailable'
  // Plain report dates must not shift into another day in the viewer's timezone.
  const day = new Date(value.length === 10 ? `${value}T00:00:00` : value)
  if (Number.isNaN(day.getTime())) return 'Unavailable'
  return includeTime
    ? day.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : day.toLocaleDateString('en-IN', { dateStyle: 'medium' })
}
export const featureNames: Record<string, string> = {
  fund_sector_share: 'Fund allocation to this sector',
  fund_industry_share: 'Fund allocation to this industry',
  fund_concentration: 'Holdings concentration',
  past_fund_additions: 'Previous fund additions',
  past_stock_additions: 'Previous additions of this stock',
  return_5: 'Return over 5 observations',
  return_20: 'Return over 20 observations',
  volatility_20: 'Daily log-return volatility',
  volume_ratio_5_20: 'Volume ratio: 5 / 20 observations',
  market_available: 'Market data available',
  event_direction: 'Extracted event direction',
  event_available: 'Extracted event data available',
}
export function featureValue(key: string, value: number | null) {
  if (value === null) return 'Unavailable'
  if (key.endsWith('_available')) return value ? 'Yes' : 'No'
  if (
    ['fund_sector_share', 'fund_industry_share', 'return_5', 'return_20', 'volatility_20'].includes(
      key,
    )
  )
    return `${(value * 100).toFixed(2)}%`
  if (key.startsWith('past_')) return value.toLocaleString('en-IN')
  return value.toFixed(3)
}
export const modelNames: Record<string, string> = {
  addition_frequency: 'Historical addition frequency',
  fund_preference: 'Fund sector / industry preference',
  holdings_market_model: 'Holdings + market model',
  full_event_model: 'Holdings + market + events',
}
