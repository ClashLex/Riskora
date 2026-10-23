import type { PropsWithChildren } from 'react'
export function RemoteState({ loading, error, retry, children }: PropsWithChildren<{ loading: boolean; error: string; retry: () => void }>) {
  if (loading) return <div className="card" role="status">Loading analysis from the service…</div>
  if (error) return <div className="card" role="alert"><h2>Analysis unavailable</h2><p>{error}</p><button className="btn secondary" onClick={retry}>Retry</button></div>
  return <>{children}</>
}
