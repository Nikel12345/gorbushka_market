import { ApiError, getFieldErrors, type FieldErrors, type ProductFilterParams } from '@/shared/api'

/** Ключи фильтров в URL — совпадают с параметрами API */
const KEYS = ['q', 'price_min', 'price_max', 'in_stock', 'category'] as const

export function parseProductFilters(params: URLSearchParams): ProductFilterParams {
  const filters: ProductFilterParams = {}
  const q = params.get('q')?.trim()
  if (q) filters.q = q
  const priceMin = normalizePrice(params.get('price_min') ?? '')
  if (priceMin) filters.price_min = priceMin
  const priceMax = normalizePrice(params.get('price_max') ?? '')
  if (priceMax) filters.price_max = priceMax
  const inStock = params.get('in_stock')
  if (inStock === 'true' || inStock === 'false') filters.in_stock = inStock === 'true'
  const category = Number(params.get('category'))
  if (Number.isInteger(category) && category > 0) filters.category = category
  return filters
}

/** Изменения для updateSearchParams: все ключи фильтров, пустые — удалить. */
export function productFiltersToSearch(filters: ProductFilterParams): Record<string, string | null> {
  const values: Record<(typeof KEYS)[number], string | undefined> = {
    q: filters.q,
    price_min: filters.price_min,
    price_max: filters.price_max,
    in_stock: filters.in_stock === undefined ? undefined : String(filters.in_stock),
    category: filters.category === undefined ? undefined : String(filters.category),
  }
  return Object.fromEntries(KEYS.map((key) => [key, values[key] || null]))
}

export function countActiveFilters(filters: ProductFilterParams): number {
  return [
    filters.q,
    filters.price_min || filters.price_max,
    filters.in_stock !== undefined,
    filters.category !== undefined,
  ].filter(Boolean).length
}

/**
 * Цена из поля ввода → "1299.90". Пустая строка — "", некорректная — null.
 * Принимает пробелы между разрядами и запятую.
 */
export function normalizePrice(input: string): string | null {
  const value = input.replace(/\s/g, '').replace(',', '.')
  if (value === '') return ''
  return /^\d+(\.\d{1,2})?$/.test(value) ? value : null
}

/** 400 на списке товаров — это ошибки значений фильтров: их показывает панель. Иначе undefined. */
export function getProductFilterErrors(error: unknown): FieldErrors | undefined {
  return error instanceof ApiError && error.status === 400 ? getFieldErrors(error) : undefined
}
