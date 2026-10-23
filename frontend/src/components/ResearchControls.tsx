import type { Research } from '../hooks/useResearch'
import type { Horizon } from '../domain'

export function FundSelect({ research: r }: { research: Research }) {
  return (
    <label>
      Fund
      <select
        value={r.fundId}
        disabled={!r.funds.length}
        onChange={(event) => r.chooseFund(event.target.value)}
      >
        {!r.funds.length && <option value="">No funds available</option>}
        {r.funds.map((fund) => (
          <option key={fund.id} value={fund.id}>
            {fund.name}
            {fund.source_kind === 'synthetic' ? ' · Sample' : ''}
          </option>
        ))}
      </select>
    </label>
  )
}
export function HorizonSelect({ research: r }: { research: Research }) {
  return (
    <label>
      Prediction period
      <select
        value={r.horizon}
        onChange={(event) => r.chooseHorizon(event.target.value as Horizon)}
      >
        <option value="month">Next monthly disclosure</option>
        <option value="quarter">Next quarterly disclosure</option>
      </select>
    </label>
  )
}
