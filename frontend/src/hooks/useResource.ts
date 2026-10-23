import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api'

/** Each response belongs to its URL. A late response cannot populate a new selection. */
export function useResource<T>(path: string | null, revision = 0) {
  const [attempt, setAttempt] = useState(0)
  const version = `${revision}:${attempt}`
  const [state, setState] = useState<{
    path: string
    version: string
    data?: T
    error?: string
    loading: boolean
  }>()
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    void api<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState({ path, version, data, loading: false })
      })
      .catch((reason) => {
        if (!controller.signal.aborted)
          setState((previous) => ({
            path,
            version,
            data: previous?.path === path ? previous.data : undefined,
            error: `${errorMessage(reason)}${previous?.path === path && previous.data ? ' Previously loaded data may be out of date.' : ''}`,
            loading: false,
          }))
      })
    return () => controller.abort()
  }, [path, version])
  const current = state?.path === path ? state : undefined
  return {
    data: current?.data,
    error: current?.version === version ? current.error : undefined,
    loading: !!path && (!current || current.version !== version || current.loading),
    retry: () => setAttempt((value) => value + 1),
  }
}
