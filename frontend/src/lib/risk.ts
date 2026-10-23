import { constituents, usdPerUnit } from '../data'
import type { Constituent, Currency, Holding, ImpactRow, Result, Scenario } from '../types'

export function convert(amount: number, from: Currency, to: Currency) {
  if (!Number.isFinite(amount) || !Number.isFinite(usdPerUnit[from]) || !Number.isFinite(usdPerUnit[to]) || usdPerUnit[to] <= 0) throw new Error('Missing or invalid illustrative FX rate')
  return amount * usdPerUnit[from] / usdPerUnit[to]
}
export const value = (holding: Holding, base: Currency) => convert(holding.marketValue, holding.currency, base)
export const total = (holdings: Holding[], base: Currency) => holdings.reduce((sum, h) => sum + value(h, base), 0)
export function aggregate(holdings: Holding[], base: Currency, key: (h: Holding) => string) {
  const groups = new Map<string, { amount: number; count: number }>()
  for (const h of holdings) { const name = key(h); const current = groups.get(name) ?? { amount: 0, count: 0 }; groups.set(name, { amount: current.amount + value(h, base), count: current.count + 1 }) }
  return [...groups].map(([name, item]) => ({ name, ...item })).sort((a, b) => b.amount - a.amount)
}
export function lookThrough(holdings: Holding[], base: Currency, mappings: Constituent[] = constituents) {
  const rows: { name: string; source: string; amount: number; sector: string }[] = []
  for (const holding of holdings) {
    const parts = mappings.filter(c => c.fundId === holding.id)
    if (parts.length) {
      if (parts.some(p => !Number.isFinite(p.weight) || p.weight < 0 || p.weight > 1) || Math.abs(parts.reduce((s, p) => s + p.weight, 0) - 1) > 1e-8) throw new Error('Illustrative fund weights must sum to 100%')
      for (const part of parts) rows.push({ name: part.name, source: holding.name, amount: value(holding, base) * part.weight, sector: part.sector })
    } else rows.push({ name: holding.name, source: 'Direct holding', amount: value(holding, base), sector: holding.sector ?? 'Unclassified' })
  }
  return rows
}
export function runSimulation(holdings: Holding[], base: Currency, scenario: Scenario, assetShock = scenario.assetShock, fxShock = scenario.fxShock, sector = scenario.sector ?? 'All sectors'): Result {
  if (![assetShock, fxShock].every(n => Number.isFinite(n) && n >= -100 && n <= 100)) throw new Error('Shocks must be finite percentages between -100 and 100')
  const rows: ImpactRow[] = holdings.map(holding => {
    const before = value(holding, base)
    const parts = constituents.filter(p => p.fundId === holding.id)
    const sectorWeight = sector === 'All sectors' ? 1 : parts.length ? parts.filter(p => p.sector === sector).reduce((s, p) => s + p.weight, 0) : holding.sector === sector ? 1 : 0
    const priceApplies = scenario.type === 'market' || scenario.type === 'combined' ? !['cash', 'bond'].includes(holding.assetClass) : ['sector', 'custom'].includes(scenario.type) ? sectorWeight > 0 && holding.assetClass !== 'cash' : false
    const assetReturn = priceApplies ? assetShock / 100 * (['sector', 'custom'].includes(scenario.type) ? sectorWeight : 1) : 0
    // fxReturn measures the change in base units per one holding-currency unit. USD/base scenarios are undefined when base=USD.
    const fxApplies = ['fx', 'combined', 'custom'].includes(scenario.type) && base !== 'USD' && holding.currency === 'USD'
    const fxReturn = fxApplies ? fxShock / 100 : 0
    const modelled = priceApplies || fxApplies
    const after = before * (1 + assetReturn) * (1 + fxReturn)
    return { holding, before, assetReturn, fxReturn, change: after - before, after, modelled }
  })
  const before = rows.reduce((s, r) => s + r.before, 0)
  const change = rows.reduce((s, r) => s + r.change, 0)
  return { scenario, currency: base, rows, before, change, after: before + change, date: new Date().toISOString() }
}
