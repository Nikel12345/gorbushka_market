import type { CartLine } from './cart'
import { apiRequest, type ApiRequestInit } from './client'
import type { DeliveryMethod, DeliveryMethodBrief } from './delivery'
import type { PaymentMethodCode, Purchase } from './purchases'
import type { ShopBrief } from './seller'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Позиция, которую можно оформить (CheckoutItemSerializer) */
export interface CheckoutItem extends CartLine {
  /** Из чего выбирать; пустым не бывает — такие позиции уходят в unavailable_items */
  delivery_methods: DeliveryMethod[]
  /** Где забрать при самовывозе из павильона */
  pickup_address: string | null
}

/** Позиция, которая не будет оформлена и останется в корзине */
export interface CheckoutUnavailableItem extends CartLine {
  problem: { code: string; detail: string }
}

/** GET /me/checkout/ (CheckoutPreviewSerializer) */
export interface CheckoutPreview {
  items: CheckoutItem[]
  unavailable_items: CheckoutUnavailableItem[]
  items_total: string
  payment_methods: { code: PaymentMethodCode; name: string }[]
  /** Деньги на балансе — для оплаты «С баланса» */
  balance: string
  /** Бонусы — переключатель «оплатить бонусами» */
  bonus: string
  /** Какую часть итога можно оплатить бонусами ("0.50") */
  bonus_max_share: string
  can_checkout: boolean
}

/** Отправка: позиции с одинаковой доставкой, за доставку платят один раз */
export interface PlannedShipment {
  delivery_method: DeliveryMethodBrief
  /** Магазин — у доставки силами продавца (самовывоз); null — логистика маркета */
  shop: ShopBrief | null
  price: string
  product_ids: number[]
}

/** POST /me/checkout/quote/ (CheckoutPlanSerializer) */
export interface CheckoutPlan {
  shipments: PlannedShipment[]
  items_total: string
  delivery_total: string
  /** Итог до бонусов — его отправляют в expected_total */
  total_amount: string
  /** Сколько спишется бонусами (если включены) */
  bonus_amount: string
  /** Итог минус бонусы: спишется с баланса или оплачивается при получении */
  amount_to_pay: string
}

export interface DeliveryChoice {
  product_id: number
  delivery_method_id: number
}

export interface SlotChoice {
  delivery_method_id: number
  /** YYYY-MM-DD */
  date: string
  window_id: number
}

export interface CheckoutPayload {
  items: DeliveryChoice[]
  /** Одно время на каждый способ с выбором времени */
  slots?: SlotChoice[]
  /** Обязателен, если выбран способ с requires_address */
  address?: string
  payment_method: PaymentMethodCode
  comment?: string
  /** Оплатить часть бонусами (не больше bonus_max_share итога) */
  use_bonus?: boolean
  /** Итог до бонусов, который видел покупатель; не совпал с пересчитанным — 409 */
  expected_total: string
}

const CHECKOUT = '/me/checkout/'

export const checkoutApi = {
  get: (options?: RequestOptions) => apiRequest<CheckoutPreview>(CHECKOUT, options),

  /** Отправки и суммы для выбранных способов. 409 cart_changed — корзина изменилась. */
  quote: (items: DeliveryChoice[], useBonus: boolean, options?: RequestOptions) =>
    apiRequest<CheckoutPlan>(`${CHECKOUT}quote/`, { method: 'POST', json: { items, use_bonus: useBonus }, ...options }),

  /** Оформить. 409 — корзина или сумма изменились, нужно перечитать. */
  place: (payload: CheckoutPayload) => apiRequest<Purchase>(CHECKOUT, { method: 'POST', json: payload }),
}
