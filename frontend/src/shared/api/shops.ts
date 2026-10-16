import { apiRequest, type ApiRequestInit } from './client'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Магазин для покупателя (ShopPublicSerializer). Товары — лента /catalog/products/?shop= */
export interface ShopPublic {
  id: number
  name: string
  description: string
  /** Где на рынке: павильон, ряд, место. Пусто — не указан */
  address: string
  /** Товаров на продаже */
  products_count: number
  created_at: string
}

export const shopsApi = {
  /** 404 — магазина нет или он скрыт от покупателей */
  get: (id: number, options?: RequestOptions) => apiRequest<ShopPublic>(`/shops/${id}/`, options),
}
