type ValidationIssue = { loc?: (string | number)[]; msg?: string }

function detailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail))
    return (detail as ValidationIssue[])
      .map((issue) => {
        const field = issue.loc
          ?.filter((part) => !['body', 'query', 'path'].includes(String(part)))
          .join(' → ')
        return `${field ? `${field}: ` : ''}${issue.msg || 'Invalid value'}`
      })
      .join('; ')
  return null
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, options)
  } catch (reason) {
    if (options?.signal?.aborted) throw reason
    throw new Error('The server could not be reached. Check the connection and retry.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok)
    throw new Error(
      detailMessage(payload?.detail) || `Request failed (${response.status}). Please retry.`,
    )
  if (payload === null) throw new Error('The server returned an unreadable response. Please retry.')
  return payload as T
}

export const errorMessage = (reason: unknown) =>
  reason instanceof Error ? reason.message : 'Something went wrong. Please retry.'
