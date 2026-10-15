import { createContext } from 'react'

/** anonymous — корзины нет (не вошёл), loading — ещё не знаем, что в ней */
export type CartStatus = 'anonymous' | 'loading' | 'ready' | 'error'

export interface CartContextValue {
  status: CartStatus
  /** Сколько штук всего лежит в корзине — для значка в шапке */
  itemsCount: number
  /** Сколько штук этого товара в корзине (0 — нет) */
  quantityOf: (productId: number) => number
  /** Идёт запрос по этому товару — кнопки блокируются, чтобы клики не обгоняли друг друга */
  isPending: (productId: number) => boolean
  /** +1 штука (или положить в корзину). Ошибку бросает — показывает её вызывающий. */
  add: (productId: number) => Promise<void>
  /** Задать количество, 0 — убрать. Ошибку бросает. */
  setQuantity: (productId: number, quantity: number) => Promise<void>
}

export const CartContext = createContext<CartContextValue | null>(null)
