/** Адрес ленты с поиском и/или категорией */
export function catalogLink(q?: string, category?: number): string {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (category) params.set('category', String(category))
  const search = params.toString()
  return search ? `/?${search}` : '/'
}

/** Каталог на главной — <main id="catalog"> в AppLayout */
export function scrollToCatalog() {
  document.getElementById('catalog')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** Ключи фильтров ленты: с любым из них главная — это уже выдача, без первого экрана и промо */
const FILTER_KEYS = ['q', 'price_min', 'price_max', 'in_stock', 'category']

export function hasCatalogFilters(searchParams: URLSearchParams): boolean {
  return FILTER_KEYS.some((key) => searchParams.get(key))
}
