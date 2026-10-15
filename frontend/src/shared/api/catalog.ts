import { apiRequest, type ApiRequestInit } from './client'
import { productFilterQuery, type ProductFilterParams } from './productFilters'
import { withQuery } from './query'
import type { ShopBrief } from './seller'
import type { CursorPage } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Товар в публичной ленте (ProductCardSerializer) */
export interface ProductCard {
  id: number
  title: string
  /** Денежные поля приходят строкой ("79990.00") */
  price: string
  /** URL фото, null — фото нет, показывается заглушка */
  image: string | null
  in_stock: boolean
  shop: ShopBrief
  created_at: string
}

/** Страница товара (ProductPublicDetailSerializer) */
export interface ProductDetail extends ProductCard {
  description: string
  quantity: number
}

/** Сортировки ленты (ProductFeedPagination.sort_options) */
export const PRODUCT_SORTS = ['new', 'price_asc', 'price_desc'] as const
export type ProductSort = (typeof PRODUCT_SORTS)[number]

export interface ProductFeedParams extends ProductFilterParams {
  /** Только товары одного магазина — для страницы магазина */
  shop?: number
  sort?: ProductSort
  /** Позиция из next_cursor предыдущей порции; без него — с начала */
  cursor?: string
}

export const catalogApi = {
  feed: ({ shop, sort, cursor, ...filters }: ProductFeedParams = {}, options?: RequestOptions) =>
    apiRequest<CursorPage<ProductCard>>(
      withQuery('/catalog/products/', { ...productFilterQuery(filters), shop, sort, cursor }),
      options,
    ),

  /** 404 — товара нет или он снят с продажи */
  getProduct: (id: number, options?: RequestOptions) => apiRequest<ProductDetail>(`/catalog/products/${id}/`, options),
}
