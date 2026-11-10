import { useCallback, useEffect, useRef, useState, type UIEvent } from 'react'
import { catalogApi, type Category, type CursorPage, type ProductCard, type ProductDetail } from '@/shared/api'
import { useRequest } from '@/shared/lib'

/** Запрос с повторами: при обрыве связи блоки витрины не остаются пустыми до перезагрузки */
async function withRetry<T>(request: () => Promise<T>, attempts = 3): Promise<T> {
  for (let attempt = 1; ; attempt++) {
    try {
      return await request()
    } catch (error) {
      // 404 и прочие ответы сервера не повторяем — только сетевые сбои и 5xx
      const status = (error as { status?: number }).status
      if (attempt >= attempts || (status !== undefined && status < 500)) throw error
      await new Promise((resolve) => setTimeout(resolve, 800 * attempt))
    }
  }
}

// --- Товары по id: для композиций из макета (одни и те же товары на первом экране, в промо, избранном) ---

const productRequests = new Map<number, Promise<ProductDetail>>()

function loadProduct(id: number): Promise<ProductDetail> {
  let request = productRequests.get(id)
  if (!request) {
    request = withRetry(() => catalogApi.getProduct(id)).catch((error: unknown) => {
      productRequests.delete(id)
      throw error
    })
    productRequests.set(id, request)
  }
  return request
}

const EMPTY_PRODUCTS = new Map<number, ProductDetail>()

/** Товары по списку id; снятые с продажи (404) просто пропускаются */
export function useProductsByIds(ids: readonly number[]) {
  const key = ids.join(',')
  const load = useCallback(async () => {
    const list = key ? key.split(',').map(Number) : []
    const results = await Promise.allSettled(list.map(loadProduct))
    return new Map(
      results.flatMap((result) => (result.status === 'fulfilled' ? [[result.value.id, result.value] as const] : [])),
    )
  }, [key])
  const request = useRequest(load)
  return { products: request.data ?? EMPTY_PRODUCTS, loaded: request.status !== 'loading' }
}

// --- Категории: один запрос на всю витрину (полоса под шапкой, главная, заголовок ленты) ---

let categoriesRequest: Promise<Category[]> | null = null

function loadCategories(): Promise<Category[]> {
  categoriesRequest ??= withRetry(() => catalogApi.categories()).catch((error: unknown) => {
    // Не получилось — следующий экран попробует ещё раз
    categoriesRequest = null
    throw error
  })
  return categoriesRequest
}

/** Категории каталога плоским списком. Пока грузятся или при ошибке — пустой список. */
export function useCategories(): Category[] {
  const [categories, setCategories] = useState<Category[]>([])
  useEffect(() => {
    let alive = true
    loadCategories().then(
      (list) => {
        if (alive) setCategories(list)
      },
      () => {},
    )
    return () => {
      alive = false
    }
  }, [])
  return categories
}

// --- Товары для первого экрана и промо-блоков ---

const never = () => new Promise<CursorPage<ProductCard>>(() => {})

/**
 * Товары в наличии по запросу и/или категории (по slug), сначала дешёвые: первый — «от N ₽» для промо.
 * Категория ещё не известна (список не загрузился) — запрос ждёт. Пусто — промо-блок не показывается.
 */
export function usePromoProducts(q: string | undefined, categorySlug: string | undefined, limit = 3) {
  const categories = useCategories()
  const category = categorySlug ? categories.find((item) => item.slug === categorySlug)?.id : undefined
  const ready = !categorySlug || category !== undefined

  const load = useCallback(
    (signal: AbortSignal) =>
      ready ? catalogApi.feed({ q, category, in_stock: true, sort: 'price_asc' }, { signal }) : never(),
    [ready, q, category],
  )
  const request = useRequest(load)
  return {
    products: request.data?.results.slice(0, limit) ?? [],
    categoryId: category,
    loaded: request.status === 'success',
  }
}

const loadLatest = (signal: AbortSignal) => catalogApi.feed({ in_stock: true, sort: 'new' }, { signal })

/** Свежие товары с фото — для «витринных» композиций первого экрана */
export function useLatestProducts(limit: number): ProductCard[] {
  const request = useRequest(loadLatest)
  return (request.data?.results ?? []).filter((product) => product.image).slice(0, limit)
}

// --- Полосы прокрутки: видны, только пока листают ---

const SCROLLBAR_HIDE_MS = 900

/** Для горизонтальных лент (класс .x-scroll): onScroll ставит is-scrolling на время прокрутки */
export function useScrollFlash<T extends HTMLElement>() {
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])
  return useCallback((event: UIEvent<T>) => {
    const element = event.currentTarget
    element.classList.add('is-scrolling')
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => element.classList.remove('is-scrolling'), SCROLLBAR_HIDE_MS)
  }, [])
}

/** То же для прокрутки страницы: класс is-scrolling на <html> */
export function usePageScrollFlash(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const root = document.documentElement
    let timer: number | undefined
    const onScroll = () => {
      root.classList.add('is-scrolling')
      window.clearTimeout(timer)
      timer = window.setTimeout(() => root.classList.remove('is-scrolling'), SCROLLBAR_HIDE_MS)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.clearTimeout(timer)
      root.classList.remove('is-scrolling')
    }
  }, [enabled])
}

// --- Движение ---

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Блок проявляется, когда доезжает до экрана: класс is-revealed (стили — .sf-reveal в Storefront.css) */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (typeof IntersectionObserver === 'undefined' || prefersReducedMotion()) {
      element.classList.add('is-revealed')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed')
            observer.unobserve(entry.target)
          }
        }
      },
      { rootMargin: '0px 0px -10% 0px' },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return ref
}

/**
 * Насколько первый экран уехал вверх: 0…1 в CSS-переменную --hero-p. По ней в CSS расходятся слова,
 * раскрывается веер товаров, гаснет фон. Без анимаций (prefers-reduced-motion) — всегда 0.
 */
export function useHeroProgress<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const element = ref.current
    if (!element || prefersReducedMotion()) return
    let frame = 0
    const update = () => {
      frame = 0
      const rect = element.getBoundingClientRect()
      const progress = Math.min(1, Math.max(0, -rect.top / Math.max(1, rect.height)))
      element.style.setProperty('--hero-p', progress.toFixed(3))
    }
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [])
  return ref
}
