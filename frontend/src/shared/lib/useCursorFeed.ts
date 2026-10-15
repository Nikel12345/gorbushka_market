import { useCallback, useEffect, useRef, useState } from 'react'

interface FeedPage<T> {
  next_cursor: string | null
  results: T[]
}

type FeedState<T> = {
  items: T[]
  nextCursor: string | null
  /** Первая порция ещё ни разу не пришла */
  initial: boolean
  /** Что сейчас грузится: лента заново (фильтры сменились) или следующая порция */
  loading: 'replace' | 'more' | null
  error: unknown
  /** На чём упала загрузка — чтобы «Повторить» повторил именно её */
  failed: 'replace' | 'more' | null
}

interface FeedCacheOptions {
  /** Ключ ленты (обычно location.search): под ним запоминается загруженное */
  key: string
  /** Показать запомненное вместо загрузки — при «назад» к ленте, чтобы вернуться на то же место */
  restore: boolean
}

interface CachedFeed {
  items: unknown[]
  nextCursor: string | null
}

// Память на время жизни вкладки, последние несколько лент
const feedCache = new Map<string, CachedFeed>()
const FEED_CACHE_SIZE = 10

function remember(key: string, feed: CachedFeed) {
  feedCache.delete(key)
  feedCache.set(key, feed)
  if (feedCache.size > FEED_CACHE_SIZE) feedCache.delete(feedCache.keys().next().value!)
}

function restoredState<T>(cache: FeedCacheOptions | undefined): FeedState<T> | null {
  const cached = cache?.restore ? feedCache.get(cache.key) : undefined
  if (!cached) return null
  return { items: cached.items as T[], nextCursor: cached.nextCursor, initial: false, loading: null, error: null, failed: null }
}

/**
 * Бесконечная лента по курсору. `load` должен быть стабильным (useCallback от фильтров):
 * при его смене лента грузится заново, а старые карточки видны, пока не придёт новая порция.
 */
export function useCursorFeed<T>(
  load: (cursor: string | undefined, signal: AbortSignal) => Promise<FeedPage<T>>,
  cache?: FeedCacheOptions,
) {
  const [state, setState] = useState<FeedState<T>>(
    () =>
      restoredState<T>(cache) ?? {
        items: [],
        nextCursor: null,
        initial: true,
        loading: 'replace',
        error: null,
        failed: null,
      },
  )
  const controllerRef = useRef<AbortController | null>(null)
  const cacheKey = cache?.key
  const restore = cache?.restore ?? false

  const fetchPage = useCallback(
    (cursor?: string) => {
      const mode = cursor ? 'more' : 'replace'
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller
      setState((prev) => ({ ...prev, loading: mode, error: null, failed: null }))

      load(cursor, controller.signal).then(
        (page) => {
          if (controller.signal.aborted) return
          setState((prev) => {
            const items = mode === 'more' ? [...prev.items, ...page.results] : page.results
            if (cacheKey !== undefined) remember(cacheKey, { items, nextCursor: page.next_cursor })
            return { items, nextCursor: page.next_cursor, initial: false, loading: null, error: null, failed: null }
          })
        },
        (error: unknown) => {
          if (controller.signal.aborted) return
          setState((prev) => ({ ...prev, loading: null, error, failed: mode }))
        },
      )
    },
    [load, cacheKey],
  )

  useEffect(() => {
    const restored = restoredState<T>(cacheKey === undefined ? undefined : { key: cacheKey, restore })
    if (restored) setState(restored)
    else fetchPage()
    return () => controllerRef.current?.abort()
  }, [fetchPage, cacheKey, restore])

  const { nextCursor, loading, failed } = state
  const hasMore = nextCursor !== null

  const loadMore = useCallback(() => {
    if (nextCursor && !loading) fetchPage(nextCursor)
  }, [fetchPage, nextCursor, loading])

  const retry = useCallback(() => {
    if (failed === 'more' && nextCursor) fetchPage(nextCursor)
    else fetchPage()
  }, [failed, fetchPage, nextCursor])

  return { ...state, hasMore, loadMore, retry }
}
