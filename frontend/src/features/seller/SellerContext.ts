import { createContext } from 'react'
import type { SellerProfile, ShopBrief } from '@/shared/api'

export interface SellerContextValue {
  profile: SellerProfile
  /** Магазин из URL, иначе последний открытый, иначе первый. null — магазинов нет. */
  activeShopId: number | null
  /** Добавить только что созданный магазин без перезагрузки профиля */
  addShop: (shop: ShopBrief) => void
}

export const SellerContext = createContext<SellerContextValue | null>(null)
