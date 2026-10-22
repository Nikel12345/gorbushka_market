import { createContext } from 'react'
import type { Shop } from '@/shared/api'

export interface SellerContextValue {
  /** Магазин (GET /admin/shop/) — шапка, адрес для самовывоза в форме товара, профиль магазина */
  shop: Shop
  /** Заменить магазин после сохранения его профиля (адрес в форме товара) */
  updateShop: (shop: Shop) => void
}

export const SellerContext = createContext<SellerContextValue | null>(null)
