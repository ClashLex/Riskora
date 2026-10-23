import { useState } from 'react'
import type { Holding, Page } from '../domain'
import { dateLabel } from '../domain'
import type { Research } from '../hooks/useResearch'
import { FundSelect } from '../components/ResearchControls'
import {
  DataTable,
  Empty,
  ErrorState,
  Facts,
  Loading,
  Section,
  Source,
  SourceNotice,
} from '../components/ui'

function allocation(holdings: Holding[], key: 'sector' | 'industry'): [string, string][] {
  const totals = new Map<string, number>()
  for (const holding of holdings) {
    const name = holding[key] || 'Unclassified'
    totals.set(name, (totals.get(name) || 0) + holding.weight)
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => [name, `${value.toFixed(2)}%`])
}
export function FundPage({
  research: r,
  navigate,
}: {
  research: Research
  navigate: (page: Page) => void
}) {
  const [snapshotId, setSnapshotId] = useState(0)
  const fund = r.fund.data
  const snapshot = fund?.snapshots.find((item) => item.id === snapshotId) || fund?.snapshots[0]
  return (
    <>
      <div className="toolbar">
        <FundSelect research={r} />
        <button className="secondary" onClick={() => navigate('Predictions')} disabled={!r.fundId}>
          Open predictions
        </button>
      </div>
      <ErrorState message={r.fund.error || r.fundsResource.error} retry={r.refresh} />
      {r.fund.loading || r.fundsResource.loading ? (
        <Loading>Loading fund disclosures…</Loading>
      ) : !fund ? (
        <Empty title="No fund disclosures available">
          <p>Import at least one dated portfolio statement to browse holdings.</p>
          <button className="primary" onClick={() => navigate('Data management')}>
            Import disclosures
          </button>
        </Empty>
      ) : (
        <>
          <SourceNotice source={fund.scheme.source_kind} />
          <div className="fund-heading">
            <h2>{fund.scheme.name}</h2>
            <p>
              {fund.scheme.amc}
              {fund.scheme.category ? ` · ${fund.scheme.category}` : ''}
            </p>
          </div>
          <Section
            title="Disclosed holdings"
            description="Select a report date. Publication date is when the statement became available."
          >
            <label className="snapshot-select">
              Report date
              <select
                value={snapshot?.id || ''}
                onChange={(event) => setSnapshotId(Number(event.target.value))}
              >
                {fund.snapshots.map((item) => (
                  <option key={item.id} value={item.id}>
                    {dateLabel(item.report_date)} · {item.complete ? 'Complete' : 'Incomplete'}
                  </option>
                ))}
              </select>
            </label>
            {snapshot && (
              <>
                <div className="snapshot-meta">
                  <span>Published {dateLabel(snapshot.published_at)}</span>
                  <span>{snapshot.weight_total.toFixed(2)}% total weight</span>
                  <Source url={snapshot.source_url} />
                </div>
                {!snapshot.complete && (
                  <p className="warning">
                    Incomplete statement. An absent stock cannot be treated as a verified negative.
                  </p>
                )}
                {snapshot.warnings.map((warning) => (
                  <p className="warning" key={warning}>
                    {warning}
                  </p>
                ))}
                <DataTable
                  key={snapshot.id}
                  caption="Disclosed holdings"
                  rows={snapshot.holdings}
                  rowKey={(row) => row.isin}
                  search={(row) => `${row.company} ${row.isin} ${row.sector || ''}`}
                  initialSort={{ key: 'weight', descending: true }}
                  columns={[
                    {
                      key: 'company',
                      label: 'Company',
                      sort: (row) => row.company,
                      render: (row) => <strong>{row.company}</strong>,
                    },
                    {
                      key: 'isin',
                      label: 'ISIN',
                      render: (row) => <span className="mono">{row.isin}</span>,
                    },
                    {
                      key: 'sector',
                      label: 'Sector',
                      sort: (row) => row.sector,
                      render: (row) => row.sector || 'Unclassified',
                    },
                    {
                      key: 'weight',
                      label: 'Weight',
                      numeric: true,
                      sort: (row) => row.weight,
                      render: (row) => `${row.weight.toFixed(2)}%`,
                    },
                    {
                      key: 'units',
                      label: 'Units',
                      numeric: true,
                      sort: (row) => row.units,
                      render: (row) => row.units?.toLocaleString('en-IN') ?? 'Unavailable',
                    },
                  ]}
                />
                <details className="disclosure">
                  <summary>Sector and industry allocation</summary>
                  <div className="two-col">
                    <div>
                      <h3>By sector</h3>
                      <Facts items={allocation(snapshot.holdings, 'sector')} />
                    </div>
                    <div>
                      <h3>By industry</h3>
                      <Facts items={allocation(snapshot.holdings, 'industry')} />
                    </div>
                  </div>
                </details>
              </>
            )}
          </Section>
          <Section
            title="Changes between disclosures"
            description="Up to 200 changes returned by the server, across monthly and quarterly comparisons. Incomplete or unaligned periods are labelled unknown."
          >
            <DataTable
              caption="Disclosure changes"
              rows={fund.changes}
              rowKey={(row) => `${row.isin}:${row.cutoff}:${row.horizon}`}
              empty="At least two comparable statements and known securities are needed to identify changes."
              initialSort={{ key: 'date', descending: true }}
              columns={[
                {
                  key: 'isin',
                  label: 'ISIN',
                  render: (row) => <span className="mono">{row.isin}</span>,
                },
                {
                  key: 'date',
                  label: 'Prior cutoff',
                  sort: (row) => row.cutoff,
                  render: (row) => dateLabel(row.cutoff),
                },
                {
                  key: 'report',
                  label: 'Next report',
                  render: (row) => dateLabel(row.target_report_date),
                },
                {
                  key: 'period',
                  label: 'Period',
                  render: (row) => (row.horizon === 'month' ? 'Monthly' : 'Quarterly'),
                },
                {
                  key: 'change',
                  label: 'Change',
                  sort: (row) => row.label,
                  render: (row) => row.label,
                },
              ]}
            />
          </Section>
        </>
      )}
    </>
  )
}
