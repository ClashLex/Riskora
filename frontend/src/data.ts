import type { Constituent, Currency, Holding, Scenario } from './types'

export const currencies: Currency[] = ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'CAD', 'AUD', 'CHF']
export const assetLabels = { stock: 'Stock', etf: 'ETF', mutual_fund: 'Mutual fund', bond: 'Bond', cash: 'Cash', other: 'Other' }
export const demoDate = '2026-01-15'
// Illustrative units of USD for one unit of the named currency; NOT live FX quotes.
export const usdPerUnit: Record<Currency, number> = { USD: 1, EUR: 1.09, GBP: 1.28, INR: 0.012, JPY: 0.0067, CAD: 0.74, AUD: 0.66, CHF: 1.13 }
export const demoHoldings: Holding[] = [
  { id: 'northstar', name: 'Northstar Global Equity ETF', ticker: 'NSGE', assetClass: 'etf', marketValue: 28500, currency: 'USD', country: 'Global', sector: 'Diversified', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'atlas', name: 'Atlas Technology Fund', ticker: 'ATLF', assetClass: 'mutual_fund', marketValue: 19800, currency: 'USD', country: 'Global', sector: 'Technology', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'meridian', name: 'Meridian Global Fund', ticker: 'MRGF', assetClass: 'mutual_fund', marketValue: 16300, currency: 'EUR', country: 'Global', sector: 'Diversified', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'semico', name: 'Example Semiconductor Co.', ticker: 'EXSC', assetClass: 'stock', marketValue: 11200, currency: 'USD', country: 'United States', sector: 'Technology', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'infrastructure', name: 'Example Infrastructure Group', ticker: 'EXIG', assetClass: 'stock', marketValue: 720000, currency: 'INR', country: 'India', sector: 'Industrials', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'treasury', name: 'Global Treasury Basket', ticker: 'GTBY', assetClass: 'bond', marketValue: 13500, currency: 'USD', country: 'Global', sector: 'Government', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
  { id: 'cash', name: 'Cash Reserve', assetClass: 'cash', marketValue: 8200, currency: 'EUR', country: 'Euro area', sector: 'Cash', sourceLabel: 'Illustrative sample asset', asOfDate: demoDate, isDemo: true },
]
// Each illustrative fund is fully allocated; these are not published fund holdings.
export const constituents: Constituent[] = [
  { fundId: 'northstar', name: 'Example Semiconductor Co.', weight: .12, sector: 'Technology' },
  { fundId: 'northstar', name: 'Example Cloud Systems', weight: .18, sector: 'Technology' },
  { fundId: 'northstar', name: 'Example Consumer Group', weight: .35, sector: 'Consumer' },
  { fundId: 'northstar', name: 'Other illustrative assets', weight: .35, sector: 'Other' },
  { fundId: 'atlas', name: 'Example Semiconductor Co.', weight: .28, sector: 'Technology' },
  { fundId: 'atlas', name: 'Example Cloud Systems', weight: .42, sector: 'Technology' },
  { fundId: 'atlas', name: 'Other illustrative technology', weight: .30, sector: 'Technology' },
  { fundId: 'meridian', name: 'Example Semiconductor Co.', weight: .10, sector: 'Technology' },
  { fundId: 'meridian', name: 'Example Infrastructure Group', weight: .20, sector: 'Industrials' },
  { fundId: 'meridian', name: 'Example Healthcare Group', weight: .30, sector: 'Healthcare' },
  { fundId: 'meridian', name: 'Other illustrative assets', weight: .40, sector: 'Other' },
]
export const scenarios: Scenario[] = [
  { id: 'market', name: 'Broad market decline', description: 'A uniform fall in illustrative non-cash, non-bond asset prices.', type: 'market', assetShock: -10, fxShock: 0 },
  { id: 'tech', name: 'Technology sector decline', description: 'Technology-linked holdings decline; diversified funds use their illustrative technology weight.', type: 'sector', assetShock: -18, fxShock: 0, sector: 'Technology' },
  { id: 'usd-up', name: 'USD strengthens', description: 'A hypothetical USD appreciation against the selected non-USD base currency.', type: 'fx', assetShock: 0, fxShock: 8 },
  { id: 'usd-down', name: 'USD weakens', description: 'A hypothetical USD depreciation against the selected non-USD base currency.', type: 'fx', assetShock: 0, fxShock: -8 },
  { id: 'combined', name: 'Combined market & FX shock', description: 'Price decline combined with a USD currency movement; returns are compounded.', type: 'combined', assetShock: -12, fxShock: 5 },
  { id: 'custom', name: 'Custom scenario', description: 'Set your own hypothetical asset and FX shocks and a target sector.', type: 'custom', assetShock: -10, fxShock: 0, sector: 'All sectors' },
]
