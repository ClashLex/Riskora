import { describe, expect, it } from 'vitest'
import { constituents, demoHoldings, scenarios } from '../data'
import { aggregate, convert, lookThrough, runSimulation, total, value } from './risk'

describe('illustrative portfolio calculations', () => {
  it('converts before summing and weights total 100%', () => {
    const sum = total(demoHoldings, 'USD')
    expect(value(demoHoldings[2], 'USD')).toBeCloseTo(16300 * 1.09)
    expect(demoHoldings.reduce((s, h) => s + value(h, 'USD') / sum, 0)).toBeCloseTo(1)
    expect(aggregate(demoHoldings, 'USD', h => h.assetClass).reduce((s, r) => s + r.amount, 0)).toBeCloseTo(sum)
  })
  it('adds direct exposure and fund contributions without adding full fund twice', () => {
    const rows = lookThrough(demoHoldings, 'USD')
    const semico = rows.filter(r => r.name === 'Example Semiconductor Co.')
    expect(semico).toHaveLength(4)
    expect(semico.reduce((s, r) => s + r.amount, 0)).toBeCloseTo(11200 + 28500 * .12 + 19800 * .28 + 16300 * 1.09 * .10)
    expect(rows.reduce((s, r) => s + r.amount, 0)).toBeCloseTo(total(demoHoldings, 'USD'))
  })
  it('rejects malformed fund weights and unavailable FX assumptions', () => {
    expect(() => lookThrough(demoHoldings, 'USD', [{ ...constituents[0], weight: 1.1 }])).toThrow()
    expect(() => convert(10, 'USD', 'XYZ' as 'USD')).toThrow()
  })
  it('applies a -10% price shock to 20,000 exposure as -2,000', () => {
    const holding = { ...demoHoldings[0], marketValue: 20000 }
    const result = runSimulation([holding], 'USD', scenarios[0])
    expect(result.change).toBeCloseTo(-2000)
    expect(result.after).toBeCloseTo(result.before + result.change)
  })
  it('handles FX gains and losses and compounds combined shocks', () => {
    const holding = { ...demoHoldings[0], marketValue: 10000 }
    const up = runSimulation([holding], 'EUR', scenarios[2])
    const down = runSimulation([holding], 'EUR', scenarios[3])
    expect(up.change).toBeGreaterThan(0)
    expect(down.change).toBeLessThan(0)
    const combined = runSimulation([holding], 'EUR', scenarios[4], -10, 5)
    expect(combined.after / combined.before).toBeCloseTo(.9 * 1.05)
    expect(combined.after).toBeCloseTo(combined.before + combined.change)
  })
  it('rejects invalid scenario inputs', () => {
    expect(() => runSimulation(demoHoldings, 'USD', scenarios[0], Number.NaN)).toThrow()
    expect(() => runSimulation(demoHoldings, 'USD', scenarios[0], -101)).toThrow()
  })
})
