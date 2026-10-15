import { createContext } from 'react'
import type { Shop } from '@/shared/api'

export interface SellerContextValue {
  /** Магазины продавца (GET /seller/shops/) — меню, адрес для самовывоза, выбор магазина в заказах */
  shops: Shop[]
  /** Магазин из URL, иначе последний открытый, иначе первый. null — магазинов нет. */
  activeShopId: number | null
  /** Добавить только что созданный магазин без перезагрузки списка */
  addShop: (shop: Shop) => void
  /** Заменить магазин после сохранения его профиля (название в меню, адрес в форме товара) */
  updateShop: (shop: Shop) => void
}

export const SellerContext = createContext<SellerContextValue | null>(null)
