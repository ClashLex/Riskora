import { useState } from 'react'
import { IconSearch } from '@tabler/icons-react'
import type { Fund } from '../domain'
import { dateLabel, sourceName } from '../domain'

export function FundBrowser({
  funds,
  selectedId,
  onSelect,
}: {
  funds: Fund[]
  selectedId: string
  onSelect: (id: string) => void
}) {
  const [query, setQuery] = useState('')
  const [source, setSource] = useState('all')
  const filtered = funds.filter(
    (fund) =>
      (source === 'all' || fund.source_kind === source) &&
      `${fund.name} ${fund.amc}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  )

  return (
    <aside className="fund-browser" aria-label="Fund library">
      <div className="fund-browser-heading">
        <h2>Fund library</h2>
        <span>{funds.length}</span>
      </div>
      <div className="fund-browser-filters">
        <label>
          Find a fund
          <span className="search-field">
            <IconSearch size={17} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name or AMC"
            />
          </span>
        </label>
        <label>
          Data source
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            <option value="all">All data</option>
            <option value="user_import">Imported</option>
            <option value="synthetic">Synthetic sample</option>
          </select>
        </label>
      </div>
      <ul className="fund-browser-list">
        {filtered.map((fund) => (
          <li key={fund.id}>
            <button
              type="button"
              aria-pressed={fund.id === selectedId}
              onClick={() => onSelect(fund.id)}
            >
              <strong>{fund.name}</strong>
              <span>
                {sourceName(fund.source_kind)} · {fund.observations} disclosures
              </span>
              <small>Report {dateLabel(fund.latest_report_date)}</small>
            </button>
          </li>
        ))}
      </ul>
      {!funds.length && (
        <p className="fund-browser-empty">No funds yet. Import disclosures to add one.</p>
      )}
      {!!funds.length && !filtered.length && (
        <p className="fund-browser-empty">No funds match these filters.</p>
      )}
    </aside>
  )
}
