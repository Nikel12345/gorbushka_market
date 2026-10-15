import type { ProductCard } from './catalog'
import { apiRequest, type ApiRequestInit } from './client'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Позиция корзины (CartLineSerializer) */
export interface CartLine {
  product: ProductCard
  quantity: number
  /** Денежные поля приходят строкой */
  total: string
  /** Можно оформить в текущем количестве */
  is_available: boolean
  /** Сколько можно купить сейчас (0 — снят с продажи или закончился) */
  available_quantity: number
}

/** Корзина целиком (CartSerializer). Её же возвращает каждое изменение. */
export interface Cart {
  items: CartLine[]
  /** Сумма количеств всех позиций */
  items_count: number
  total_amount: string
  has_unavailable: boolean
}

const CART = '/me/cart/'

export const cartApi = {
  get: (options?: RequestOptions) => apiRequest<Cart>(CART, options),

  /** Положить товар; если он уже в корзине — количество прибавляется */
  add: (productId: number, quantity = 1) =>
    apiRequest<Cart>(`${CART}items/`, { method: 'POST', json: { product_id: productId, quantity } }),

  /** Задать количество; 0 — убрать товар */
  setQuantity: (productId: number, quantity: number) =>
    apiRequest<Cart>(`${CART}items/${productId}/`, { method: 'PATCH', json: { quantity } }),

  remove: (productId: number) => apiRequest<Cart>(`${CART}items/${productId}/`, { method: 'DELETE' }),

  clear: () => apiRequest<Cart>(CART, { method: 'DELETE' }),
}
