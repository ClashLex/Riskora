import { dateLabel, modelNames, periodName, sourceName } from '../domain'
import type { Metrics, SourceKind } from '../domain'
import type { Research } from '../hooks/useResearch'
import { HorizonSelect } from '../components/ResearchControls'
import {
  DataTable,
  Empty,
  ErrorState,
  Facts,
  Loading,
  Section,
  SourceNotice,
  TokenInput,
} from '../components/ui'

const metric = (value?: number | null) =>
  value === null || value === undefined ? 'Unavailable' : value.toFixed(3)
export function EvaluationPage({ research: r }: { research: Research }) {
  const readiness = r.readiness.data,
    run = r.selectedRun
  const training = r.pending === 'Training and evaluating'
  const rows: ({ name: string } & Metrics)[] = Object.entries(run?.metrics || {}).map(
    ([name, values]) => ({ name, ...values }),
  )
  return (
    <>
      <div className="toolbar">
        <label>
          Training dataset
          <select
            value={r.evaluationSource}
            onChange={(event) => r.setEvaluationSource(event.target.value as SourceKind)}
          >
            <option value="user_import">Imported data</option>
            <option value="synthetic">Synthetic sample</option>
          </select>
        </label>
        <HorizonSelect research={r} />
      </div>
      <SourceNotice source={r.evaluationSource} />
      <ErrorState message={r.readiness.error || r.runsResource.error} retry={r.refresh} />
      <div className="two-col">
        <Section
          title="Training readiness"
          description="Training uses all eligible funds in this dataset and period."
        >
          {r.readiness.loading ? (
            <Loading>Checking comparable history…</Loading>
          ) : (
            readiness && (
              <>
                <Facts
                  items={[
                    ['Comparable cutoff periods', readiness.usable_periods],
                    ['Verified additions', readiness.label_counts.addition || 0],
                    ['Verified negatives', readiness.label_counts.negative || 0],
                    ['Unknown cases (excluded)', readiness.label_counts.unknown || 0],
                  ]}
                />
                <p className={readiness.ready ? 'readiness-ready' : 'muted'}>
                  {readiness.ready
                    ? 'History meets the minimum training requirements.'
                    : 'More comparable history is needed.'}
                </p>
                <ul className="check-list">
                  {readiness.blockers?.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <p className="muted">{readiness.requirements}</p>
              </>
            )
          )}
        </Section>
        <Section
          title="Train and evaluate"
          description="Fits on earlier available labels, validates on later cutoffs, and holds the final cutoff out for testing."
        >
          <div className="control-stack">
            <TokenInput value={r.token} onChange={r.setToken} />
            <button
              className="primary"
              onClick={() => void r.train()}
              disabled={!!r.pending || r.readiness.loading || !readiness?.ready || !r.token}
            >
              {training ? 'Training and evaluating…' : 'Train and evaluate'}
            </button>
          </div>
          <p className="muted">
            {!r.token
              ? 'Enter the management token to enable training.'
              : !readiness?.ready
                ? 'Training becomes available when the data requirements are met.'
                : 'Each completed run saves its model and evaluation results.'}
          </p>
        </Section>
      </div>
      {training && (
        <Loading>
          Training models and calculating later-period results. This may take a while.
        </Loading>
      )}
      {r.runsResource.loading ? (
        <Loading>Loading saved evaluations…</Loading>
      ) : !run ? (
        <Empty title="No evaluation for this selection">
          <p>
            No saved run matches {sourceName(r.evaluationSource).toLocaleLowerCase()} and the{' '}
            {periodName(r.horizon).toLocaleLowerCase()} period.
          </p>
        </Empty>
      ) : (
        <>
          <Section title="Saved evaluation">
            {!run.current_method && (
              <p className="warning">
                Legacy evaluation: this run predates the publication-date checks. Retrain before
                using its results. Legacy models are excluded from new rankings.
              </p>
            )}
            <label className="run-select">
              Evaluation run
              <select
                value={run.id}
                onChange={(event) => r.setChosenRun(Number(event.target.value))}
              >
                {r.scopedRuns.map((item) => (
                  <option key={item.id} value={item.id}>
                    Run #{item.id} · {item.model_version} · {dateLabel(item.finished_at, true)}
                  </option>
                ))}
              </select>
            </label>
            <Facts
              items={[
                ['Training cutoffs through', dateLabel(run.train_end)],
                ['Final holdout cutoff', dateLabel(run.test_start)],
                ['Model version', run.model_version],
                [
                  'Dataset and period',
                  `${sourceName(run.source_kind)} · ${periodName(run.horizon)}`,
                ],
              ]}
            />
            <h3 className="subheading">Final holdout comparison</h3>
            <DataTable
              caption="Holdout comparison"
              rows={rows}
              rowKey={(row) => row.name}
              columns={[
                {
                  key: 'model',
                  label: 'Model / baseline',
                  render: (row) => modelNames[row.name] || row.name,
                },
                { key: 'cases', label: 'Cases', numeric: true, render: (row) => row.cases ?? '—' },
                {
                  key: 'positive',
                  label: 'Additions',
                  numeric: true,
                  render: (row) => row.positives ?? '—',
                },
                {
                  key: 'precision',
                  label: 'Precision@5',
                  numeric: true,
                  render: (row) => metric(row.precision_at_5),
                },
                {
                  key: 'recall',
                  label: 'Recall@5',
                  numeric: true,
                  render: (row) => metric(row.recall_at_5),
                },
                {
                  key: 'ap',
                  label: 'Avg. precision',
                  numeric: true,
                  render: (row) => metric(row.average_precision),
                },
              ]}
            />
            {rows
              .filter((row) => row.reason)
              .map((row) => (
                <p className="muted" key={row.name}>
                  {modelNames[row.name]}: {row.reason}
                </p>
              ))}
            <details className="disclosure">
              <summary>How to read these metrics</summary>
              <dl className="definitions">
                <dt>Precision@5</dt>
                <dd>
                  The share of additions among the top five candidates, averaged across fund/cutoff
                  groups. Groups with fewer candidates use their actual count.
                </dd>
                <dt>Recall@5</dt>
                <dd>
                  The share of eligible additions captured in the top five, averaged over groups
                  containing additions.
                </dd>
                <dt>Average precision</dt>
                <dd>
                  A ranking summary over all evaluated cases. It is unavailable when no positive
                  cases are present.
                </dd>
              </dl>
              <p className="muted">
                The candidate universe excludes stocks unknown at the cutoff. These metrics do not
                measure performance on all possible market securities.
              </p>
            </details>
          </Section>
          <Section
            title={`Validation and holdout periods · run #${run.id}`}
            description="Earlier labels are included in training only when the target statement was published by the evaluation cutoff."
          >
            <ErrorState message={r.backtests.error} retry={r.refresh} />
            {r.backtests.loading ? (
              <Loading>Loading this run’s evaluation periods…</Loading>
            ) : (
              <DataTable
                caption="Evaluation periods"
                rows={r.backtests.data || []}
                rowKey={(row) => `${row.phase}:${row.period}:${row.model}`}
                columns={[
                  { key: 'phase', label: 'Phase', render: (row) => row.phase },
                  { key: 'date', label: 'Cutoff', render: (row) => dateLabel(row.period) },
                  {
                    key: 'model',
                    label: 'Model / baseline',
                    render: (row) => modelNames[row.model] || row.model,
                  },
                  {
                    key: 'cases',
                    label: 'Cases',
                    numeric: true,
                    render: (row) => row.metrics.cases ?? '—',
                  },
                  {
                    key: 'precision',
                    label: 'Precision@5',
                    numeric: true,
                    render: (row) => metric(row.metrics.precision_at_5),
                  },
                  {
                    key: 'recall',
                    label: 'Recall@5',
                    numeric: true,
                    render: (row) => metric(row.metrics.recall_at_5),
                  },
                ]}
              />
            )}
          </Section>
        </>
      )}
    </>
  )
}
