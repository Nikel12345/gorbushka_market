import { Navigate } from 'react-router'
import { useSeller } from '@/features/seller'

/** /seller — ведёт в товары текущего магазина, а если магазинов нет — к созданию первого. */
export function SellerHomePage() {
  const { activeShopId } = useSeller()

  return <Navigate to={activeShopId !== null ? `/seller/shops/${activeShopId}/products` : '/seller/shops/new'} replace />
}
