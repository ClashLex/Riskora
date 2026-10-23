import { useEffect, useRef, useState } from 'react'
import type { Page } from './domain'
import { useResearch } from './hooks/useResearch'
import { Workspace } from './components/Workspace'
import { pageFromHash, pageHash } from './navigation'
import { OverviewPage } from './pages/OverviewPage'
import { FundPage } from './pages/FundPage'
import { PredictionsPage } from './pages/PredictionsPage'
import { EvidencePage } from './pages/EvidencePage'
import { EvaluationPage } from './pages/EvaluationPage'
import { DataPage } from './pages/DataPage'

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash)
  const research = useResearch()
  const errorSummary = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (research.error) errorSummary.current?.focus()
  }, [research.error])
  useEffect(() => {
    const sync = () => setPage(pageFromHash())
    window.addEventListener('hashchange', sync)
    window.addEventListener('popstate', sync)
    return () => {
      window.removeEventListener('hashchange', sync)
      window.removeEventListener('popstate', sync)
    }
  }, [])
  useEffect(() => {
    document.title = `${page === 'Evidence' ? 'Supporting signals' : page} · Riskora`
  }, [page])
  function navigate(next: Page) {
    if (next !== page) window.history.pushState(null, '', pageHash(next))
    setPage(next)
    document.getElementById('main-content')?.focus({ preventScroll: true })
    window.scrollTo?.({ top: 0, behavior: 'instant' })
  }
  return (
    <Workspace
      page={page}
      navigate={navigate}
      funds={research.funds}
      fundId={research.fundId}
      selectFund={research.chooseFund}
      refresh={research.refresh}
      busy={!!research.pending}
    >
      {research.error && (
        <div ref={errorSummary} className="alert error" role="alert" tabIndex={-1}>
          <p>{research.error}</p>
          <button className="text-button" onClick={research.clearMessages}>
            Dismiss
          </button>
        </div>
      )}
      {research.notice && (
        <div className="alert success" role="status">
          <p>{research.notice}</p>
          <button className="text-button" onClick={research.clearMessages}>
            Dismiss
          </button>
        </div>
      )}
      {research.pending && (
        <p className="operation-status" role="status">
          {research.pending}…
        </p>
      )}
      {page === 'Overview' && <OverviewPage research={research} navigate={navigate} />}
      {page === 'Fund explorer' && <FundPage research={research} navigate={navigate} />}
      {page === 'Predictions' && <PredictionsPage research={research} navigate={navigate} />}
      {page === 'Evidence' && <EvidencePage research={research} navigate={navigate} />}
      {page === 'Evaluation' && <EvaluationPage research={research} />}
      {page === 'Data management' && <DataPage research={research} />}
    </Workspace>
  )
}
