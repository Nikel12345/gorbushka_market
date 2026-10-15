import { useCallback, useEffect, useState } from 'react'

export type RequestState<T> =
  | { status: 'loading'; data: T | undefined; error: null }
  | { status: 'success'; data: T; error: null }
  | { status: 'error'; data: T | undefined; error: unknown }

/**
 * Загрузка данных для страницы. `request` должен быть стабильным (useCallback
 * или функция вне компонента) — при его смене запрос перезапускается,
 * а предыдущий отменяется. Во время перезагрузки старые данные остаются в `data`.
 *
 * Когда понадобится кэш/инвалидация — меняется на TanStack Query с тем же
 * набором полей (status/data/error/reload), страницы почти не трогаются.
 */
export function useRequest<T>(request: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<RequestState<T>>({
    status: 'loading',
    data: undefined,
    error: null,
  })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState((prev) => ({ status: 'loading', data: prev.data, error: null }))

    request(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ status: 'success', data, error: null })
      },
      (error: unknown) => {
        if (!controller.signal.aborted) setState((prev) => ({ status: 'error', data: prev.data, error }))
      },
    )

    return () => controller.abort()
  }, [request, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])

  /** Локально поправить загруженные данные, не перезапрашивая их. */
  const mutate = useCallback((updater: (data: T) => T) => {
    setState((prev) => (prev.status === 'success' ? { ...prev, data: updater(prev.data) } : prev))
  }, [])

  return { ...state, reload, mutate }
}
