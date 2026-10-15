import { useContext } from 'react'
import { useParams } from 'react-router'
import type { Shop } from '@/shared/api'
import { SellerContext } from './SellerContext'

export function useSeller() {
  const context = useContext(SellerContext)
  if (!context) {
    throw new Error('useSeller must be used within SellerContext (SellerLayout)')
  }
  return context
}

/** Магазин из URL (/seller/shops/:shopId/...). Доступен только внутри ShopRoute. */
export function useCurrentShop(): Shop {
  const { shopId } = useParams()
  const { shops } = useSeller()
  const shop = shops.find((item) => String(item.id) === shopId)
  if (!shop) {
    throw new Error('useCurrentShop must be used within ShopRoute')
  }
  return shop
}
