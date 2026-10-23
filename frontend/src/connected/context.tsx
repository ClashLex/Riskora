import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { api } from '../services/api'
import type { ApiPortfolio, ApiResult, ApiSummary } from '../services/api'
import type { Currency } from '../types'

type ContextValue = { portfolio: ApiPortfolio | null; portfolios: ApiSummary[]; selected: string; select: (id: string) => void; loading: boolean; error: string; retry: () => void; refresh: () => Promise<void>; create: (name: string, currency: Currency) => Promise<void>; revision: number; history: ApiResult[]; result: ApiResult | null; saveResult: (r: ApiResult) => void; clearResult: () => void }
const Context = createContext<ContextValue | null>(null)
export function ConnectedProvider({ children }: PropsWithChildren) {
  const [selected, setSelected] = useState(() => sessionStorage.getItem('risvanta-api-portfolio') || 'demo-global')
  const [portfolio, setPortfolio] = useState<ApiPortfolio | null>(null)
  const [portfolios, setPortfolios] = useState<ApiSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [history, setHistory] = useState<ApiResult[]>([])
  const [result, setResult] = useState<ApiResult | null>(null)
  useEffect(() => {
    let current = true
    setLoading(true); setError(''); setPortfolio(null)
    Promise.all([api.portfolios(), api.portfolio(selected)]).then(([list, detail]) => { if (current) { setPortfolios(list); setPortfolio(detail); setLoading(false) } }).catch(e => { if (current) { setError(e instanceof Error ? e.message : 'Unable to load portfolio'); setLoading(false) } })
    return () => { current = false }
  }, [selected, attempt])
  const refresh = useCallback(async () => { const [list, detail] = await Promise.all([api.portfolios(), api.portfolio(selected)]); setPortfolios(list); setPortfolio(detail); setResult(null); setRevision(v => v + 1) }, [selected])
  const create = async (name: string, currency: Currency) => { const created = await api.createPortfolio(name, currency); setSelected(created.id); sessionStorage.setItem('risvanta-api-portfolio', created.id) }
  const select = (id: string) => { sessionStorage.setItem('risvanta-api-portfolio', id); setHistory([]); setResult(null); setSelected(id) }
  const saveResult = (r: ApiResult) => { setResult(r); setHistory(previous => [r, ...previous].slice(0, 5)) }
  return <Context.Provider value={{ portfolio, portfolios, selected, select, loading, error, retry: () => setAttempt(v => v + 1), refresh, create, revision, history, result, saveResult, clearResult: () => setResult(null) }}>{children}</Context.Provider>
}
export function useConnected() { const context = useContext(Context); if (!context) throw new Error('Missing connected provider'); return context }

export function useRemote<T>(load: () => Promise<T>, deps: readonly unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  // Callers pass stable primitive dependency values; the request is invalidated on cleanup.
  useEffect(() => { let current = true; setLoading(true); setData(null); setError(''); load().then(value => { if (current) { setData(value); setLoading(false) } }).catch(e => { if (current) { setError(e instanceof Error ? e.message : 'Unable to load analysis'); setLoading(false) } }); return () => { current = false } }, [...deps, attempt]) // eslint-disable-line react-hooks/exhaustive-deps
  return { data, error, loading, retry: () => setAttempt(v => v + 1) }
}
