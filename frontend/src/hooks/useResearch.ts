import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorMessage } from '../api'
import { periodName, sourceName } from '../domain'
import type {
  Backtest,
  Candidate,
  Evidence,
  Fund,
  FundDetail,
  Horizon,
  Identifier,
  Overview,
  Prediction,
  Readiness,
  Run,
  SourceKind,
} from '../domain'
import { useResource } from './useResource'

export function useResearch() {
  const [revision, setRevision] = useState(0)
  const [chosenFund, setChosenFund] = useState('')
  const [horizon, setHorizon] = useState<Horizon>('month')
  const [evaluationSource, setEvaluationSource] = useState<SourceKind>('user_import')
  const [chosenRun, setChosenRun] = useState<number | null>(null)
  const [token, setToken] = useState('')
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [predictionState, setPrediction] = useState<{ key: string; value: Prediction }>()
  const [selectedIsin, setSelectedIsin] = useState('')
  const [lastEventId, setLastEventId] = useState<number | null>(null)
  const operation = useRef<AbortController | null>(null)
  const overview = useResource<Overview>('/overview', revision)
  const fundsResource = useResource<Fund[]>('/funds', revision)
  const funds = fundsResource.data || []
  const selectedFund = funds.find((item) => item.id === chosenFund) || funds[0]
  const fundId = selectedFund?.id || ''
  const fund = useResource<FundDetail>(
    fundId ? `/funds/${encodeURIComponent(fundId)}` : null,
    revision,
  )
  const runsResource = useResource<Run[]>('/training-runs', revision)
  const runs = runsResource.data || []
  const readiness = useResource<Readiness>(
    `/readiness?horizon=${horizon}&source_kind=${evaluationSource}`,
    revision,
  )
  const scopedRuns = runs.filter(
    (run) => run.source_kind === evaluationSource && run.horizon === horizon,
  )
  const selectedRun = scopedRuns.find((run) => run.id === chosenRun) || scopedRuns[0]
  const backtests = useResource<Backtest[]>(
    selectedRun ? `/backtests?run_id=${selectedRun.id}` : null,
    revision,
  )
  const identifiers = useResource<Identifier[]>('/identifiers', revision)
  const contextKey = `${fundId}:${horizon}:${revision}`
  const prediction = predictionState?.key === contextKey ? predictionState.value : undefined
  const selected = prediction?.candidates.find((candidate) => candidate.isin === selectedIsin)
  const evidence = useResource<Evidence>(
    selected && prediction
      ? `/evidence/${encodeURIComponent(fundId)}/${encodeURIComponent(selected.isin)}?cutoff=${prediction.cutoff}`
      : null,
    revision,
  )
  const canRank =
    !!fundId &&
    runs.some(
      (run) =>
        run.status === 'complete' &&
        run.current_method &&
        run.source_kind === selectedFund?.source_kind &&
        run.horizon === horizon,
    )

  useEffect(
    () => () => {
      operation.current?.abort()
    },
    [],
  )
  // Invalidate ranking requests immediately when their fund/period/data context changes.
  const currentContext = useRef(contextKey)
  useLayoutEffect(() => {
    currentContext.current = contextKey
  }, [contextKey])
  const refresh = () => {
    setRevision((value) => value + 1)
    setError('')
    setNotice('')
  }
  const clearMessages = () => {
    setError('')
    setNotice('')
  }

  async function act(label: string, work: (signal: AbortSignal) => Promise<void>) {
    if (operation.current) return
    const controller = new AbortController()
    operation.current = controller
    setPending(label)
    setError('')
    setNotice('')
    try {
      await work(controller.signal)
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason))
    } finally {
      operation.current = null
      if (!controller.signal.aborted) setPending('')
    }
  }

  const auth = { 'X-Admin-Token': token }
  function jsonOptions(body: unknown, signal: AbortSignal): RequestInit {
    return {
      method: 'POST',
      headers: { ...auth, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    }
  }
  function chooseFund(id: string) {
    setChosenFund(id)
    setSelectedIsin('')
    setError('')
  }
  function chooseHorizon(value: Horizon) {
    setHorizon(value)
    setSelectedIsin('')
    setError('')
  }
  async function rank() {
    if (!canRank) return
    const key = contextKey
    await act('Ranking candidates', async (signal) => {
      try {
        const value = await api<Prediction>(
          `/predictions/${encodeURIComponent(fundId)}?horizon=${horizon}`,
          { signal },
        )
        if (currentContext.current === key && !signal.aborted) {
          setPrediction({ key, value })
          setSelectedIsin('')
        }
      } catch (reason) {
        if (currentContext.current === key) throw reason
      }
    })
  }
  async function upload(event: FormEvent<HTMLFormElement>, kind: 'holdings' | 'market') {
    event.preventDefault()
    const form = event.currentTarget
    const body = new FormData(form)
    const file = body.get('file')
    if (file instanceof File && file.size > 5 * 1024 * 1024) {
      setError('Choose a CSV file no larger than 5 MB.')
      return
    }
    if (kind === 'holdings') body.set('complete', String(body.get('complete') === 'true'))
    await act(`Importing ${kind}`, async (signal) => {
      const result = await api<{ rows: number; complete?: boolean; warnings?: string[] }>(
        `/imports/${kind}`,
        { method: 'POST', headers: auth, body, signal },
      )
      setNotice(
        `Imported ${result.rows} ${kind} rows.${result.complete === false ? ' The statement is incomplete.' : ''} ${result.warnings?.join(' ') || ''}`.trim(),
      )
      form.reset()
      setRevision((value) => value + 1)
    })
  }
  async function train() {
    await act('Training and evaluating', async (signal) => {
      const result = await api<{ run_id: number; test_period: string }>(
        '/training-runs',
        jsonOptions({ horizon, source_kind: evaluationSource }, signal),
      )
      setChosenRun(result.run_id)
      setNotice(
        `Run #${result.run_id} completed for ${sourceName(evaluationSource).toLowerCase()}, ${periodName(horizon).toLowerCase()} period. Holdout cutoff: ${result.test_period}.`,
      )
      setRevision((value) => value + 1)
    })
  }
  async function loadDemo() {
    await act('Loading synthetic sample', async (signal) => {
      const result = await api<{ snapshots: number; status: string }>('/demo/load', {
        method: 'POST',
        headers: auth,
        signal,
      })
      setNotice(
        `${result.snapshots} synthetic snapshots ${result.status === 'loaded' ? 'loaded' : 'already present'}. Sample results do not measure real predictive performance.`,
      )
      setEvaluationSource('synthetic')
      setRevision((value) => value + 1)
    })
  }
  async function importEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const body = Object.fromEntries(new FormData(form).entries())
    await act('Importing event', async (signal) => {
      body.published_at = new Date(String(body.published_at)).toISOString()
      const result = await api<{ event_id: number }>('/events', jsonOptions(body, signal))
      setLastEventId(result.event_id)
      setNotice(`Event #${result.event_id} imported.`)
      form.reset()
    })
  }
  async function extractEvent() {
    if (lastEventId === null) return
    await act('Extracting event facts', async (signal) => {
      await api(`/events/${lastEventId}/extract`, { method: 'POST', headers: auth, signal })
      setNotice(
        `Event #${lastEventId} extracted. Only extractions available by a ranking cutoff can be used as model inputs.`,
      )
    })
  }
  async function reviewIdentifier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = Object.fromEntries(new FormData(form).entries())
    await act('Saving identifier review', async (signal) => {
      await api(`/identifiers/${encodeURIComponent(String(fields.isin).trim().toUpperCase())}`, {
        ...jsonOptions(
          { ticker: String(fields.ticker).trim().toUpperCase(), source_url: fields.source_url },
          signal,
        ),
        method: 'PUT',
      })
      setNotice(`Ticker mapping reviewed for ${fields.isin}.`)
      form.reset()
      setRevision((value) => value + 1)
    })
  }
  function inspect(candidate: Candidate) {
    setSelectedIsin(candidate.isin)
  }

  return {
    overview,
    fundsResource,
    funds,
    fund,
    fundId,
    selectedFund,
    chooseFund,
    horizon,
    chooseHorizon,
    evaluationSource,
    setEvaluationSource,
    runsResource,
    scopedRuns,
    selectedRun,
    setChosenRun,
    readiness,
    backtests,
    identifiers,
    token,
    setToken,
    pending,
    error,
    notice,
    refresh,
    clearMessages,
    prediction,
    selected,
    evidence,
    canRank,
    rank,
    inspect,
    upload,
    train,
    loadDemo,
    importEvent,
    extractEvent,
    reviewIdentifier,
    lastEventId,
  }
}
export type Research = ReturnType<typeof useResearch>
