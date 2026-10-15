import { config } from '@/shared/config'

export class ApiError extends Error {
  readonly status: number
  readonly data: unknown

  constructor(status: number, data: unknown) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

const CSRF_COOKIE = 'csrftoken'
const CSRF_HEADER = 'X-CSRFToken'
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

function getCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

/**
 * Django ротирует CSRF-токен при входе, поэтому значение всегда читаем из cookie
 * непосредственно перед запросом. Если cookie ещё нет — просим бэкенд её выставить.
 */
async function getCsrfToken(): Promise<string> {
  let token = getCookie(CSRF_COOKIE)
  if (!token) {
    await fetch(`${config.apiBaseUrl}/auth/csrf/`, { credentials: 'include' })
    token = getCookie(CSRF_COOKIE)
  }
  return token ?? ''
}

export interface ApiRequestInit extends Omit<RequestInit, 'body'> {
  /** Тело запроса, будет сериализовано в JSON */
  json?: unknown
  body?: BodyInit
}

/**
 * Единая точка общения с backend API: cookie-сессия, CSRF, JSON, ошибки.
 */
export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { json, headers, ...rest } = init
  const method = (rest.method ?? 'GET').toUpperCase()

  const finalHeaders = new Headers(headers)
  finalHeaders.set('Accept', 'application/json')
  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json')
  }
  if (!SAFE_METHODS.has(method)) {
    finalHeaders.set(CSRF_HEADER, await getCsrfToken())
  }

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    credentials: 'include',
    ...rest,
    method,
    headers: finalHeaders,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })

  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(response.status, data)
  }

  return data as T
}
