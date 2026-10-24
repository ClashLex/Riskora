import { useState } from 'react'
import type { Research } from '../hooks/useResearch'
import { dateLabel } from '../domain'
import { DataTable, ErrorState, Section, TokenInput } from '../components/ui'

export function DataPage({ research: r }: { research: Research }) {
  const [kind, setKind] = useState<'holdings' | 'market'>('holdings')
  const disabled = !!r.pending || !r.token
  return (
    <div className="page-design page-data">
      <Section
        title="Management access"
        description="Imports, identifier reviews, and training require the server’s management token. It stays in this browser tab’s memory."
      >
        <div className="token-input">
          <TokenInput value={r.token} onChange={r.setToken} />
        </div>
      </Section>
      <Section
        title="Import disclosures and prices"
        description="UTF-8 CSV, up to 5 MB. Convert PDF and spreadsheet disclosures before importing. Source links are retained as attribution; they are not fetched or verified."
      >
        <div className="segmented" role="group" aria-label="Import type">
          <button aria-pressed={kind === 'holdings'} onClick={() => setKind('holdings')}>
            Fund holdings
          </button>
          <button aria-pressed={kind === 'market'} onClick={() => setKind('market')}>
            Market prices
          </button>
        </div>
        {kind === 'holdings' ? (
          <>
            <h3>Import fund holdings</h3>
            <p className="muted">
              One fund and report date per file. Required columns:{' '}
              <code>isin, company, weight</code>. Weight is a percentage.{' '}
              <a href="/templates/holdings.csv" download>
                Download CSV headers
              </a>
              .
            </p>
            <form className="form" onSubmit={(event) => void r.upload(event, 'holdings')}>
              <label>
                Fund ID
                <input
                  name="scheme_id"
                  required
                  minLength={2}
                  maxLength={64}
                  pattern="[a-zA-Z0-9_-]{2,64}"
                  placeholder="e.g. example_large_cap"
                />
                <small>Use the same ID for each statement of this fund.</small>
              </label>
              <label>
                Fund name
                <input name="scheme_name" required maxLength={200} />
              </label>
              <label>
                AMC
                <input name="amc" required maxLength={200} />
              </label>
              <label>
                Category (optional)
                <input name="category" />
              </label>
              <label>
                Portfolio report date
                <input name="report_date" type="date" required />
                <small>The date the positions refer to.</small>
              </label>
              <label>
                Publication date
                <input name="published_at" type="date" required />
                <small>When this statement became public.</small>
              </label>
              <label className="wide">
                Disclosure source URL
                <input name="source_url" type="url" required placeholder="https://" />
              </label>
              <label className="wide">
                Holdings CSV
                <input name="file" type="file" accept=".csv,text/csv" required />
              </label>
              <label className="check wide">
                <input name="complete" type="checkbox" value="true" />I checked that this is a full,
                comparable portfolio statement.
              </label>
              <p className="muted wide">
                Unchecked statements, or statements totalling less than 90% weight, are stored as
                incomplete. They cannot verify that an absent stock was not held.
              </p>
              <button className="primary" disabled={disabled}>
                {r.pending === 'Importing holdings' ? 'Importing holdings…' : 'Import holdings'}
              </button>
            </form>
          </>
        ) : (
          <>
            <h3>Import market prices</h3>
            <p className="muted">
              Required columns: <code>date, isin, company, close, volume</code>. Optional adjusted
              prices help reduce distortions from corporate actions.{' '}
              <a href="/templates/market.csv" download>
                Download CSV headers
              </a>
              .
            </p>
            <form className="form" onSubmit={(event) => void r.upload(event, 'market')}>
              <label className="wide">
                Market data source URL
                <input name="source_url" type="url" required placeholder="https://" />
              </label>
              <label className="wide">
                Market CSV
                <input name="file" type="file" accept=".csv,text/csv" required />
              </label>
              <button className="primary" disabled={disabled}>
                {r.pending === 'Importing market' ? 'Importing prices…' : 'Import market data'}
              </button>
            </form>
          </>
        )}
      </Section>
      <details className="disclosure management-detail">
        <summary>Security identifiers and ticker reviews</summary>
        <p className="muted">
          ISIN is the security key. Review ticker changes with a source before importing conflicting
          mappings. This registry includes imported and synthetic securities.
        </p>
        <ErrorState message={r.identifiers.error} retry={r.refresh} />
        <DataTable
          caption="Security identifiers"
          rows={r.identifiers.data || []}
          rowKey={(row) => row.isin}
          search={(row) => `${row.company} ${row.isin} ${row.ticker || ''}`}
          columns={[
            {
              key: 'company',
              label: 'Company',
              sort: (row) => row.company,
              render: (row) => row.company,
            },
            {
              key: 'isin',
              label: 'ISIN',
              render: (row) => <span className="mono">{row.isin}</span>,
            },
            { key: 'ticker', label: 'Ticker', render: (row) => row.ticker || 'Unmapped' },
            {
              key: 'review',
              label: 'Last reviewed',
              render: (row) => (row.reviewed_at ? dateLabel(row.reviewed_at) : 'Not reviewed'),
            },
          ]}
        />
        <h3 className="subheading">Review a mapping</h3>
        <form className="form" onSubmit={(event) => void r.reviewIdentifier(event)}>
          <label>
            ISIN
            <input name="isin" required minLength={12} maxLength={12} placeholder="INE000A01010" />
          </label>
          <label>
            Exchange ticker
            <input name="ticker" required maxLength={30} />
          </label>
          <label className="wide">
            Mapping evidence URL
            <input name="source_url" type="url" required />
          </label>
          <button className="primary" disabled={disabled}>
            Save mapping review
          </button>
        </form>
      </details>
      <details className="disclosure management-detail">
        <summary>Company events and optional extraction</summary>
        <p className="muted">
          Store a public announcement or permitted excerpt for an imported security. Optional
          extraction needs a configured provider and only uses supported facts from the excerpt.
        </p>
        <form className="form" onSubmit={(event) => void r.importEvent(event)}>
          <label>
            ISIN
            <input name="isin" required pattern="IN[A-Z0-9]{10}" minLength={12} maxLength={12} />
          </label>
          <label>
            Event title
            <input name="title" required minLength={3} maxLength={200} />
          </label>
          <label>
            Category
            <input
              name="category"
              required
              minLength={2}
              maxLength={80}
              placeholder="e.g. earnings"
            />
          </label>
          <label>
            Published date and time
            <input name="published_at" type="datetime-local" required />
            <small>Your local time; stored in UTC.</small>
          </label>
          <label className="wide">
            Public source URL
            <input name="source_url" type="url" required />
          </label>
          <label className="wide">
            Permitted excerpt
            <textarea name="excerpt" required minLength={10} maxLength={10000} />
          </label>
          <button className="primary" disabled={disabled}>
            Import event
          </button>
        </form>
        {r.lastEventId !== null && (
          <div className="action-note">
            <p>
              Event #{r.lastEventId} is stored. Extraction sends this excerpt to the configured
              provider.
            </p>
            <button className="secondary" disabled={disabled} onClick={() => void r.extractEvent()}>
              Extract event facts
            </button>
          </div>
        )}
      </details>
      <Section
        title="Try sample data"
        description="Two fictional funds, 15 monthly statements, and synthetic prices. Sample data stays separate from imports."
      >
        <p className="muted">
          Sample evaluations do not measure real predictive performance. Loading again keeps the
          existing sample.
        </p>
        <button className="secondary" disabled={disabled} onClick={() => void r.loadDemo()}>
          {r.pending === 'Loading synthetic sample' ? 'Loading sample…' : 'Load synthetic sample'}
        </button>
      </Section>
    </div>
  )
}
