export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR' | 'JPY' | 'CAD' | 'AUD' | 'CHF'
export type AssetClass = 'stock' | 'etf' | 'mutual_fund' | 'bond' | 'cash' | 'other'
export type Holding = { id: string; name: string; ticker?: string; assetClass: AssetClass; marketValue: number; currency: Currency; country?: string; sector?: string; quantity?: number; sourceLabel: string; asOfDate: string; isDemo: boolean }
export type Constituent = { fundId: string; name: string; weight: number; sector: string }
export type Scenario = { id: string; name: string; description: string; type: 'market' | 'sector' | 'fx' | 'combined' | 'custom'; assetShock: number; fxShock: number; sector?: string }
export type ImpactRow = { holding: Holding; before: number; assetReturn: number; fxReturn: number; change: number; after: number; modelled: boolean }
export type Result = { scenario: Scenario; currency: Currency; before: number; after: number; change: number; rows: ImpactRow[]; date: string }
