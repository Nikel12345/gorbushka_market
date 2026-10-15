import { apiRequest, type ApiRequestInit } from './client'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** pickup — забрать у продавца (нужен адрес магазина), courier — привезут покупателю */
export type DeliveryKind = 'pickup' | 'courier'

/** Способ доставки из справочника маркета (DeliveryMethodSerializer) */
export interface DeliveryMethod {
  id: number
  code: string
  name: string
  kind: DeliveryKind
  /** Кто доставляет: продавец или логистика маркета */
  provider: 'shop' | 'market'
  description: string
  /** Стоимость для покупателя, строкой ("0.00") */
  price: string
  /** Срок в днях; null — без срока (самовывоз) */
  eta: { min_days: number; max_days: number } | null
  /** Покупателю нужно указать адрес */
  requires_address: boolean
  /** При оформлении выбирается дата и интервал */
  has_slots: boolean
}

export const deliveryApi = {
  /** Активные способы: форма товара, фильтр ленты, справка */
  methods: (options?: RequestOptions) => apiRequest<DeliveryMethod[]>('/delivery/methods/', options),
}
