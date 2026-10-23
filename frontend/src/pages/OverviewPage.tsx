import type { Page } from '../domain'
import { dateLabel, sourceName } from '../domain'
import type { Research } from '../hooks/useResearch'
import { DataTable, Empty, ErrorState, Facts, Loading, Section } from '../components/ui'

export function OverviewPage({
  research: r,
  navigate,
}: {
  research: Research
  navigate: (page: Page) => void
}) {
  const summary = r.overview.data
  return (
    <>
      <ErrorState message={r.overview.error || r.fundsResource.error} retry={r.refresh} />
      {r.overview.loading && <Loading>Loading disclosure coverage…</Loading>}
      {!summary ? null : (
        <>
          {!summary.funds ? (
            <Empty title="Start with a fund’s disclosure history">
              <p>
                Import dated portfolio statements, add market observations, then check whether there
                is enough history to train and evaluate a model.
              </p>
              <button className="primary" onClick={() => navigate('Data management')}>
                Import disclosures
              </button>
              <p className="muted">
                A clearly labelled synthetic sample is also available in Data management.
              </p>
            </Empty>
          ) : (
            <>
              <Section
                title="Disclosure coverage"
                description="Imported statements and sample history are counted separately."
              >
                <Facts
                  items={[
                    ['Imported disclosures', summary.imported_observations],
                    ['Synthetic sample disclosures', summary.synthetic_observations],
                    [
                      'Funds with a complete statement',
                      `${summary.eligible_funds} of ${summary.funds}`,
                    ],
                    ['Latest imported report date', dateLabel(summary.latest_real_report)],
                    ['Last data import', dateLabel(summary.latest_update, true)],
                  ]}
                />
              </Section>
              <Section
                title="Funds in this workspace"
                description="Choose a fund to inspect its reported holdings and publication dates."
              >
                <DataTable
                  caption="Fund coverage"
                  rows={r.funds}
                  rowKey={(fund) => fund.id}
                  search={(fund) => `${fund.name} ${fund.amc}`}
                  columns={[
                    {
                      key: 'name',
                      label: 'Fund',
                      sort: (fund) => fund.name,
                      render: (fund) => (
                        <button
                          className="text-button"
                          onClick={() => {
                            r.chooseFund(fund.id)
                            navigate('Fund explorer')
                          }}
                        >
                          {fund.name}
                        </button>
                      ),
                    },
                    {
                      key: 'source',
                      label: 'Data source',
                      render: (fund) => sourceName(fund.source_kind),
                    },
                    {
                      key: 'count',
                      label: 'Disclosures',
                      numeric: true,
                      sort: (fund) => fund.observations,
                      render: (fund) => fund.observations,
                    },
                    {
                      key: 'date',
                      label: 'Latest report',
                      sort: (fund) => fund.latest_report_date,
                      render: (fund) => dateLabel(fund.latest_report_date),
                    },
                  ]}
                />
              </Section>
            </>
          )}
          <Section title="Data checks">
            {summary.warnings.length ? (
              <ul className="check-list">
                {summary.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : (
              <p>
                No import warnings reported. This does not verify the accuracy of the supplied
                sources.
              </p>
            )}
          </Section>
          <aside className="method-note">
            <h2>What this workspace measures</h2>
            <p>
              The target is a holding that is absent from a complete disclosure and appears at a
              weight of at least 0.1% in a later disclosure. A report reveals a position, not the
              date or reason for a trade.
            </p>
            <p>
              Rankings need a trained model for the selected dataset and period. Review its
              later-period evaluation and baselines before interpreting scores.
            </p>
            <button className="text-button" onClick={() => navigate('Evaluation')}>
              Review evaluation
            </button>
          </aside>
        </>
      )}
    </>
  )
}
