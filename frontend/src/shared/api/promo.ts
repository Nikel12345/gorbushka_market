import { apiRequest, type ApiRequestInit } from './client'
import type { ShopBrief } from './seller'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Рекламная полоса (PromoSerializer) */
export interface Promo {
  id: number
  /** Для alt картинки */
  title: string
  image: string | null
  /** Узкая версия для телефона; null — показывается основная */
  image_mobile: string | null
  /** Ведёт на товары магазина (с filters) */
  shop: ShopBrief | null
  /** Параметры ленты магазина, как в адресе: {"q": "чехол", "sort": "price_asc"} */
  filters: Record<string, string>
  /** Вместо магазина: путь на сайте (/products/7) или https://…; пусто — никуда не ведёт */
  url: string
}

export const promoApi = {
  /** Случайная реклама для ленты на главной; null (204) — показывать нечего */
  feed: (options?: RequestOptions) => apiRequest<Promo | null>('/promo/feed/', options),
}
