import { IconArrowRight, IconArrowUpRight } from '@tabler/icons-react'
import type { Page } from '../domain'
import { dateLabel } from '../domain'
import type { Research } from '../hooks/useResearch'
import { Empty, ErrorState, Loading } from '../components/ui'
import { MagicBento } from '../components/MagicBento'

const count = (value: number) => value.toLocaleString('en-IN')

export function OverviewPage({
  research: r,
  navigate,
}: {
  research: Research
  navigate: (page: Page) => void
}) {
  const summary = r.overview.data
  return (
    <div className="page-design page-overview">
      <ErrorState message={r.overview.error || r.fundsResource.error} retry={r.refresh} />
      {r.overview.loading && <Loading>Loading disclosure coverage…</Loading>}
      {summary && (
        <>
          {!summary.funds && (
            <div className="overview-start">
              <Empty title="Start with a fund’s disclosure history">
                <p>
                  This workspace has no fund statements yet. Add dated portfolio disclosures to
                  explore holdings and check whether there is enough history for a model.
                </p>
                <button className="primary" onClick={() => navigate('Data management')}>
                  Manage data
                </button>
                <p className="muted">
                  You can also load a clearly labelled synthetic sample in Data management.
                </p>
              </Empty>
              <aside className="start-guide" aria-label="Data needed for a ranking">
                <h2>Before you can rank candidates</h2>
                <ol>
                  <li>Import complete fund statements with report and publication dates.</li>
                  <li>Optionally add market prices for more complete signals.</li>
                  <li>Check training readiness and review the later period evaluation.</li>
                </ol>
              </aside>
            </div>
          )}
          {!!summary.funds && (
            <div className="overview-actions">
              <button className="primary" onClick={() => navigate('Fund explorer')}>
                Explore funds <IconArrowRight size={17} aria-hidden="true" />
              </button>
              <button className="secondary" onClick={() => navigate('Evaluation')}>
                Review evaluation
              </button>
            </div>
          )}
          <section className="overview-coverage" aria-labelledby="coverage-heading">
            <div className="overview-section-title">
              <h2 id="coverage-heading">Disclosure coverage</h2>
              {summary.latest_real_report && (
                <p>Latest imported report: {dateLabel(summary.latest_real_report)}</p>
              )}
            </div>
            <MagicBento
              label="Disclosure coverage figures"
              items={[
                {
                  id: 'funds',
                  label: 'Funds tracked',
                  value: count(summary.funds),
                  colSpan: 2,
                },
                {
                  id: 'eligible',
                  label: 'With a complete statement',
                  value: count(summary.eligible_funds),
                },
                {
                  id: 'imports',
                  label: 'Imported disclosures',
                  value: count(summary.imported_observations),
                },
                {
                  id: 'sample',
                  label: 'Sample disclosures',
                  value: count(summary.synthetic_observations),
                  colSpan: 2,
                },
              ]}
            />
            {summary.latest_update && (
              <p className="overview-update">
                Last holdings import {dateLabel(summary.latest_update, true)}
              </p>
            )}
          </section>

          <div className="overview-bottom">
            <section className="overview-checks" aria-labelledby="checks-heading">
              <h2 id="checks-heading">Data checks</h2>
              {summary.warnings.length ? (
                <ul className="check-list">
                  {summary.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : (
                <p>
                  No import warnings reported. Supplied sources have not been independently
                  verified.
                </p>
              )}
            </section>
            <aside className="overview-method">
              <h2>What counts as new?</h2>
              <p>
                A holding absent from a complete disclosure that later appears at 0.1% weight or
                more. Only complete, comparable statements establish absence. Review the later
                period evaluation before interpreting a ranking.
              </p>
              <button className="text-button" onClick={() => navigate('Evaluation')}>
                Read the evaluation <IconArrowUpRight size={16} aria-hidden="true" />
              </button>
            </aside>
          </div>
        </>
      )}
    </div>
  )
}
