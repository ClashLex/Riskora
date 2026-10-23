import { createContext, useContext, useEffect, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { currencies, demoHoldings } from './data'
import { getPortfolio, resetPortfolio, savePortfolio } from './services/portfolio'
import type { Currency, Holding, Result } from './types'

type Store = { holdings: Holding[]; setHoldings: (h: Holding[]) => void; reset: () => void; clear: () => void; currency: Currency; setCurrency: (c: Currency) => void; history: Result[]; addRun: (r: Result) => void }
const Context = createContext<Store | null>(null)
export function StoreProvider({ children }: PropsWithChildren) {
  const [holdings, update] = useState<Holding[]>(getPortfolio)
  const [currency, setCurrency] = useState<Currency>(() => { const saved = localStorage.getItem('risvanta-currency'); return currencies.find(c => c === saved) ?? 'USD' })
  const [history, setHistory] = useState<Result[]>([])
  useEffect(() => { savePortfolio(holdings) }, [holdings])
  useEffect(() => { localStorage.setItem('risvanta-currency', currency) }, [currency])
  const setHoldings = (h: Holding[]) => update(h)
  const reset = () => { update(resetPortfolio()); setHistory([]) }
  const clear = () => { update([]); setHistory([]) }
  return <Context.Provider value={{ holdings, setHoldings, reset, clear, currency, setCurrency, history, addRun: r => setHistory(h => [r, ...h].slice(0, 5)) }}>{children}</Context.Provider>
}
export function useStore() { const ctx = useContext(Context); if (!ctx) throw new Error('Missing store'); return ctx }
export { demoHoldings }
