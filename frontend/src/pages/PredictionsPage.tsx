import type { Page } from '../domain'
import { dateLabel, periodName } from '../domain'
import type { Research } from '../hooks/useResearch'
import { FundSelect, HorizonSelect } from '../components/ResearchControls'
import {
  DataTable,
  Empty,
  ErrorState,
  Facts,
  Loading,
  Section,
  SourceNotice,
} from '../components/ui'

export function PredictionsPage({
  research: r,
  navigate,
}: {
  research: Research
  navigate: (page: Page) => void
}) {
  const result = r.prediction
  const ranking = r.pending === 'Ranking candidates'
  const rows =
    result?.candidates.map((candidate, index) => ({ ...candidate, rank: index + 1 })) || []
  return (
    <>
      <div className="toolbar">
        <FundSelect research={r} />
        <HorizonSelect research={r} />
        <button
          className="primary"
          onClick={() => void r.rank()}
          disabled={!!r.pending || !r.canRank}
        >
          {ranking ? 'Ranking…' : 'Rank candidates'}
        </button>
      </div>
      <ErrorState message={r.fundsResource.error || r.runsResource.error} retry={r.refresh} />
      {(r.fundsResource.loading || r.runsResource.loading) && (
        <Loading>Checking funds and available models…</Loading>
      )}
      {r.selectedFund && <SourceNotice source={r.selectedFund.source_kind} />}
      {ranking && <Loading>Building inputs and ranking candidates for the selected fund…</Loading>}
      {result ? (
        <>
          <div className="prediction-context">
            <Section
              title={`${r.selectedFund?.name} · ${periodName(result.horizon)}`}
              description="Scores rank possible new positions; they are not purchase probabilities."
            >
              <Facts
                items={[
                  ['Portfolio report date', dateLabel(result.observation_date)],
                  ['Disclosure published', dateLabel(result.published_at)],
                  ['Information cutoff', dateLabel(result.cutoff)],
                  ['Ranking generated', dateLabel(result.generated_at, true)],
                  ['Model', `${result.model_version} · run #${result.run_id}`],
                  ['Target holding', `New position ≥ ${result.materiality}% weight`],
                ]}
              />
            </Section>
          </div>
          <Section
            title="Ranked candidates"
            description="Known stocks absent from the selected complete statement. The original rank stays fixed when you sort or filter."
          >
            <DataTable
              key={`${result.run_id}:${result.cutoff}:${result.scheme_id}`}
              caption="Ranked candidates"
              rows={rows}
              rowKey={(row) => row.isin}
              search={(row) => `${row.company} ${row.isin} ${row.sector || ''}`}
              initialSort={{ key: 'rank', descending: false }}
              columns={[
                {
                  key: 'rank',
                  label: 'Rank',
                  numeric: true,
                  sort: (row) => row.rank,
                  render: (row) => row.rank,
                },
                {
                  key: 'company',
                  label: 'Company',
                  sort: (row) => row.company,
                  render: (row) => (
                    <button
                      className="text-button company-link"
                      onClick={() => {
                        r.inspect(row)
                        navigate('Evidence')
                      }}
                    >
                      {row.company}
                      <span className="sr-only">: inspect supporting signals</span>
                    </button>
                  ),
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
                  key: 'score',
                  label: 'Ranking score',
                  numeric: true,
                  sort: (row) => row.score,
                  render: (row) => row.score.toFixed(3),
                },
              ]}
            />
          </Section>
          <p className="method-note">{result.warning}</p>
        </>
      ) : (
        !ranking &&
        !r.fundsResource.loading &&
        !r.runsResource.loading && (
          <Empty
            title={r.canRank ? 'Ready to rank candidates' : 'A matching trained model is required'}
          >
            <p>
              {!r.funds.length
                ? 'Import complete holdings history and market observations, then evaluate a model.'
                : r.canRank
                  ? 'Choose a fund and disclosure period, then select Rank candidates.'
                  : 'Train a model for this fund’s dataset and disclosure period. Imported and synthetic data use separate models.'}
            </p>
            {!r.canRank && (
              <button
                className="secondary"
                onClick={() => {
                  if (r.selectedFund) r.setEvaluationSource(r.selectedFund.source_kind)
                  navigate(r.funds.length ? 'Evaluation' : 'Data management')
                }}
              >
                {r.funds.length ? 'Open evaluation' : 'Manage data'}
              </button>
            )}
          </Empty>
        )
      )}
    </>
  )
}
