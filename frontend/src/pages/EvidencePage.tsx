import type { Page } from '../domain'
import { dateLabel, featureNames, featureValue } from '../domain'
import type { Research } from '../hooks/useResearch'
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

export function EvidencePage({
  research: r,
  navigate,
}: {
  research: Research
  navigate: (page: Page) => void
}) {
  const candidate = r.selected,
    prediction = r.prediction,
    evidence = r.evidence.data
  if (!candidate || !prediction)
    return (
      <Empty title="Choose a ranked company">
        <p>
          Open a company in Predictions to inspect its model inputs, source documents, and available
          history.
        </p>
        <button className="primary" onClick={() => navigate('Predictions')}>
          Open predictions
        </button>
      </Empty>
    )
  return (
    <>
      <button className="text-button back-link" onClick={() => navigate('Predictions')}>
        ← Back to ranked candidates
      </button>
      <SourceNotice source={prediction.source_kind} />
      <div className="fund-heading">
        <h2>{candidate.company}</h2>
        <p>
          <span className="mono">{candidate.isin}</span> · {r.selectedFund?.name} · Cutoff{' '}
          {dateLabel(prediction.cutoff)}
        </p>
      </div>
      <ErrorState message={r.evidence.error} retry={r.evidence.retry} />
      {r.evidence.loading && <Loading>Loading source history…</Loading>}
      <div className="two-col">
        <Section
          title="Model inputs"
          description="Missing inputs are shown explicitly. The model imputes missing numeric values as zero before scaling."
        >
          <Facts
            items={Object.entries(candidate.features).map(([key, value]) => [
              featureNames[key] || key,
              featureValue(key, value),
            ])}
          />
        </Section>
        <Section
          title="Contributions to model score"
          description="Signed contributions to the model’s log-odds, before the intercept and sigmoid. These do not describe a fund manager’s reasoning."
        >
          <Facts
            items={Object.entries(candidate.contributions)
              .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
              .map(([key, value]) => [
                featureNames[key] || key,
                `${value >= 0 ? '+' : ''}${value.toFixed(3)}`,
              ])}
          />
        </Section>
      </div>
      <Section
        title="Sources used for these inputs"
        description="Source dates and publication dates should be read separately."
      >
        {candidate.evidence.length ? (
          candidate.evidence.map((item, index) => (
            <article className="source-row" key={`${item.source_url}:${index}`}>
              <h3>
                {item.type === 'holdings'
                  ? 'Portfolio statement'
                  : item.type === 'market'
                    ? 'Market observations'
                    : 'Extracted company event'}
              </h3>
              <p>
                Dated {dateLabel(item.date)}
                {item.published_at ? ` · Published ${dateLabel(item.published_at)}` : ''}
              </p>
              <Source url={item.source_url} />
              {item.note && <p className="muted">{item.note}</p>}
            </article>
          ))
        ) : (
          <p>No source links were returned for these inputs.</p>
        )}
      </Section>
      {evidence && (
        <>
          <Section
            title="Prior disclosed positions"
            description="Positions in this fund’s statements published by the cutoff."
          >
            {evidence.holdings.length ? (
              evidence.holdings.map((holding, index) => (
                <div className="source-row" key={index}>
                  <p>
                    Report {dateLabel(holding.report_date)} · Published{' '}
                    {dateLabel(holding.published_at)} · Weight {holding.weight.toFixed(2)}%
                  </p>
                  <Source url={holding.source_url} />
                </div>
              ))
            ) : (
              <p className="muted">No disclosed position in this fund through the cutoff.</p>
            )}
          </Section>
          <Section
            title="Company events"
            description="Up to 20 imported events published by the cutoff. An event is a model input only if its extraction was also available by that date."
          >
            {evidence.events.length ? (
              evidence.events.map((event, index) => (
                <article className="source-row" key={index}>
                  <h3>{event.title}</h3>
                  <p className="muted">Published {dateLabel(event.published_at, true)}</p>
                  <p>{event.excerpt}</p>
                  <Source url={event.source_url} />
                </article>
              ))
            ) : (
              <p className="muted">No company events available for this stock and cutoff.</p>
            )}
          </Section>
          <Section
            title="Market observations"
            description="The latest 30 observations through the cutoff. Close is the supplied, unadjusted closing price."
          >
            <DataTable
              caption="Market observations"
              rows={evidence.market}
              rowKey={(row) => row.date}
              columns={[
                { key: 'date', label: 'Date', render: (row) => dateLabel(row.date) },
                {
                  key: 'close',
                  label: 'Close',
                  numeric: true,
                  render: (row) => row.close.toFixed(2),
                },
                {
                  key: 'volume',
                  label: 'Volume',
                  numeric: true,
                  render: (row) => row.volume.toLocaleString('en-IN'),
                },
                {
                  key: 'source',
                  label: 'Source',
                  render: (row) => <Source url={row.source_url} />,
                },
              ]}
            />
          </Section>
        </>
      )}
    </>
  )
}
