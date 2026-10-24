import { useEffect, useId, useState } from 'react'
import type { ReactNode } from 'react'
import {
  IconArrowDown,
  IconArrowUp,
  IconArrowUpRight,
  IconEye,
  IconEyeOff,
  IconSearch,
  IconSelector,
} from '@tabler/icons-react'
import { sourceName } from '../domain'

export function Source({ url }: { url: string }) {
  if (!/^https?:\/\//i.test(url))
    return (
      <span className="muted">
        {url.startsWith('sample:') ? 'Synthetic source' : 'Source unavailable'}
      </span>
    )
  return (
    <a href={url} target="_blank" rel="noreferrer">
      View source <IconArrowUpRight size={14} aria-hidden="true" />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  )
}
export function Section({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="section">
      <header className="section-heading">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </header>
      {children}
    </section>
  )
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <section className="empty">
      <h2>{title}</h2>
      {children}
    </section>
  )
}
export function Loading({ children = 'Loading data…' }: { children?: ReactNode }) {
  return (
    <p className="loading" role="status">
      {children}
    </p>
  )
}
export function ErrorState({ message, retry }: { message?: string; retry: () => void }) {
  if (!message) return null
  return (
    <div className="alert error" role="alert">
      <p>{message}</p>
      <button className="secondary" onClick={retry}>
        Retry
      </button>
    </div>
  )
}
export function SourceNotice({ source }: { source: string }) {
  return source === 'synthetic' ? (
    <div className="source-notice">
      <strong>Synthetic sample</strong>
      <span>Fictional holdings and prices. Evaluation does not show real market performance.</span>
    </div>
  ) : (
    <p className="provenance">
      {sourceName(source)} · Supplied sources have not been independently verified.
    </p>
  )
}
export function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="facts">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
export function MetricStrip({
  items,
  className = '',
}: {
  items: [string, ReactNode][]
  className?: string
}) {
  return (
    <dl className={`metric-strip${className ? ` ${className}` : ''}`}>
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
export function TokenInput({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  return (
    <div className="field">
      <label htmlFor={id}>Management token</label>
      <span className="password-field">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="off"
          placeholder="Enter your management token"
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={visible ? 'Hide management token' : 'Show management token'}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? (
            <IconEyeOff size={18} aria-hidden="true" />
          ) : (
            <IconEye size={18} aria-hidden="true" />
          )}
        </button>
      </span>
    </div>
  )
}
export type Column<T> = {
  key: string
  label: string
  numeric?: boolean
  render: (row: T) => ReactNode
  sort?: (row: T) => string | number | null
}

function useCompactRecords() {
  const [compact, setCompact] = useState(
    () =>
      typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 800px)').matches,
  )
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(max-width: 800px)')
    const update = () => setCompact(media.matches)
    media.addEventListener('change', update)
    update()
    return () => media.removeEventListener('change', update)
  }, [])
  return compact
}

export function DataTable<T>({
  caption,
  rows,
  columns,
  rowKey,
  search,
  initialSort,
  empty = 'No records available.',
}: {
  caption: string
  rows: T[]
  columns: Column<T>[]
  rowKey: (row: T) => string
  search?: (row: T) => string
  initialSort?: { key: string; descending: boolean }
  empty?: string
}) {
  const id = useId()
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState(initialSort)
  const [page, setPage] = useState(0)
  const compact = useCompactRecords()
  const filtered = rows.filter(
    (row) => !search || search(row).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  )
  const column = columns.find((item) => item.key === sort?.key)
  if (column?.sort)
    filtered.sort((a, b) => {
      const first = column.sort!(a),
        second = column.sort!(b)
      if (first === null) return second === null ? 0 : 1
      if (second === null) return -1
      const order =
        typeof first === 'number' && typeof second === 'number'
          ? first - second
          : String(first).localeCompare(String(second))
      return sort?.descending ? -order : order
    })
  const size = 25
  const lastPage = Math.max(0, Math.ceil(filtered.length / size) - 1)
  const currentPage = Math.min(page, lastPage)
  const start = currentPage * size
  const visibleRows = filtered.slice(start, start + size)
  const sortableColumns = columns.filter((item) => item.sort)
  const primaryColumn = columns.find((item) => !item.numeric) || columns[0]
  return (
    <div className="data-table">
      {search && (
        <div className="table-controls">
          <label htmlFor={id}>
            Search {caption.toLocaleLowerCase()}
            <span className="search-field">
              <IconSearch size={18} aria-hidden="true" />
              <input
                id={id}
                type="search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value)
                  setPage(0)
                }}
              />
            </span>
          </label>
          <button
            className="text-button"
            onClick={() => {
              setQuery('')
              setSort(initialSort)
              setPage(0)
            }}
            disabled={
              !query &&
              sort?.key === initialSort?.key &&
              sort?.descending === initialSort?.descending
            }
          >
            Reset
          </button>
        </div>
      )}
      {compact ? (
        <>
          {sortableColumns.length > 0 && (
            <div className="mobile-sort">
              <label>
                Sort {caption.toLocaleLowerCase()}
                <select
                  value={sort?.key || ''}
                  onChange={(event) => {
                    const next = columns.find((item) => item.key === event.target.value)
                    setSort(next ? { key: next.key, descending: !!next.numeric } : undefined)
                    setPage(0)
                  }}
                >
                  <option value="">Original order</option>
                  {sortableColumns.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              {sort && (
                <button
                  className="secondary"
                  aria-label={sort.descending ? 'Sort ascending' : 'Sort descending'}
                  onClick={() => {
                    setSort((current) =>
                      current ? { ...current, descending: !current.descending } : current,
                    )
                    setPage(0)
                  }}
                >
                  {sort.descending ? (
                    <IconArrowDown size={18} aria-hidden="true" />
                  ) : (
                    <IconArrowUp size={18} aria-hidden="true" />
                  )}
                  {sort.descending ? 'Descending' : 'Ascending'}
                </button>
              )}
            </div>
          )}
          <ul className="mobile-records" aria-label={caption}>
            {visibleRows.map((row) => (
              <li className="mobile-record" key={rowKey(row)}>
                <div className="mobile-record-title">{primaryColumn.render(row)}</div>
                <dl>
                  {columns
                    .filter((item) => item.key !== primaryColumn.key)
                    .map((item) => (
                      <div className="mobile-field" key={item.key}>
                        <dt>{item.label}</dt>
                        <dd>{item.render(row)}</dd>
                      </div>
                    ))}
                </dl>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={`${caption} table`}>
          <table>
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr>
                {columns.map((item) => (
                  <th
                    key={item.key}
                    scope="col"
                    className={item.numeric ? 'numeric' : undefined}
                    aria-sort={
                      item.sort
                        ? sort?.key === item.key
                          ? sort.descending
                            ? 'descending'
                            : 'ascending'
                          : 'none'
                        : undefined
                    }
                  >
                    {item.sort ? (
                      <button
                        className="sort-button"
                        onClick={() => {
                          setSort({
                            key: item.key,
                            descending: sort?.key === item.key ? !sort.descending : !!item.numeric,
                          })
                          setPage(0)
                        }}
                      >
                        {item.label}
                        {sort?.key === item.key ? (
                          sort.descending ? (
                            <IconArrowDown size={14} aria-hidden="true" />
                          ) : (
                            <IconArrowUp size={14} aria-hidden="true" />
                          )
                        ) : (
                          <IconSelector size={14} aria-hidden="true" />
                        )}
                      </button>
                    ) : (
                      item.label
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={rowKey(row)}>
                  {columns.map((item) => (
                    <td key={item.key} className={item.numeric ? 'numeric' : undefined}>
                      {item.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!filtered.length && (
        <p className="table-empty">
          {query ? 'No matches. Change the search or reset the table.' : empty}
        </p>
      )}
      <div className="table-footer">
        <span role="status">
          {filtered.length
            ? `${start + 1}–${Math.min(start + size, filtered.length)} of ${filtered.length}`
            : '0'}
          {query ? ` matching ${rows.length} records` : ' records'}
        </span>
        {filtered.length > size && (
          <div>
            <button
              className="secondary"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              Previous
            </button>
            <button
              className="secondary"
              disabled={currentPage === lastPage}
              onClick={() => setPage(currentPage + 1)}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
