import type { QueryParams } from './query'

/**
 * Параметры единого ProductFilter бэкенда (backend/apps/catalog/filters.py).
 * Одни и те же для админки магазина и ленты на главной:
 * новый фильтр добавляется здесь и в ProductFilter.
 */
export interface ProductFilterParams {
  /** Поиск по названию и описанию */
  q?: string
  /** Десятичное число через точку: "1299.90" */
  price_min?: string
  price_max?: string
  /** true — только в наличии, false — только отсутствующие, нет — все */
  in_stock?: boolean
  /** Товары категории вместе с подкатегориями */
  category?: number
}

export function productFilterQuery(filters: ProductFilterParams): QueryParams {
  return {
    q: filters.q,
    price_min: filters.price_min,
    price_max: filters.price_max,
    in_stock: filters.in_stock === undefined ? undefined : String(filters.in_stock),
    category: filters.category,
  }
}
