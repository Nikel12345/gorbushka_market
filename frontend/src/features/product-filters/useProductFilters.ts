import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import type { ProductFilterParams } from '@/shared/api'
import { updateSearchParams } from '@/shared/lib'
import { countActiveFilters, parseProductFilters, productFiltersToSearch } from './model'

/**
 * Фильтры товаров в URL (?q=&price_min=&price_max=&in_stock=): ссылкой можно поделиться,
 * «назад» работает. Смена фильтров сбрасывает ?page.
 */
export function useProductFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  // searchParams стабилен, пока не меняется location.search
  const filters = useMemo(() => parseProductFilters(searchParams), [searchParams])

  const setFilters = useCallback(
    (next: ProductFilterParams) => {
      setSearchParams((prev) => updateSearchParams(prev, { ...productFiltersToSearch(next), page: null }))
    },
    [setSearchParams],
  )

  const resetFilters = useCallback(() => setFilters({}), [setFilters])

  return { filters, setFilters, resetFilters, activeCount: countActiveFilters(filters) }
}
