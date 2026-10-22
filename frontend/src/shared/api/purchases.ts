import { apiRequest, type ApiRequestInit } from './client'
import type { DeliveryMethodBrief } from './delivery'
import { withQuery } from './query'
import type { OrderBase, ShopBrief } from './admin'
import type { CursorPage } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

export type PaymentMethodCode = 'balance' | 'on_delivery'
/** refunded — оплачена с баланса, все заказы отменены, деньги вернулись */
export type PaymentStatus = 'unpaid' | 'paid' | 'refunded'

/** Доставка позиции заказа: способ и время (ShipmentBriefSerializer) */
export interface ShipmentBrief {
  id: number
  delivery_method: DeliveryMethodBrief
  /** Время доставки; null — способ без выбора времени */
  slot: { date: string; start: string; end: string } | null
}

/** Отправка в покупке — для покупателя (ShipmentSerializer) */
export interface Shipment extends ShipmentBrief {
  /** Магазин при самовывозе; null — логистика маркета */
  shop: ShopBrief | null
  /** Куда везти или откуда забрать; пусто — не нужно */
  address: string
  price: string
  /** Из цены доставки оплачено бонусами */
  bonus_amount: string
  /** Сколько взять за доставку при вручении (только оплата при получении) */
  amount_due: string
}

/** Заказ магазина в покупке (BuyerOrderSerializer) */
export interface BuyerOrder extends OrderBase {
  shop: ShopBrief
  purchase_id: number | null
}

/** Покупка: заказы магазинов и отправки (PurchaseSerializer) */
export interface Purchase {
  id: number
  payment_method: PaymentMethodCode
  payment_method_display: string
  payment_status: PaymentStatus
  payment_status_display: string
  items_total: string
  delivery_total: string
  total_amount: string
  /** Оплачено бонусами */
  bonus_amount: string
  comment: string
  orders: BuyerOrder[]
  shipments: Shipment[]
  created_at: string
  updated_at: string
}

/** Сортировки истории (OrderHistoryPagination.sort_options) */
export type PurchaseSort = 'new' | 'old' | 'total_desc' | 'total_asc'

export const purchasesApi = {
  /** История покупок текущего пользователя, курсор */
  list: ({ cursor, sort }: { cursor?: string; sort?: PurchaseSort } = {}, options?: RequestOptions) =>
    apiRequest<CursorPage<Purchase>>(withQuery('/me/purchases/', { cursor, sort }), options),

  /** 404 — чужая или несуществующая покупка */
  get: (id: number, options?: RequestOptions) => apiRequest<Purchase>(`/me/purchases/${id}/`, options),
}
