import { Outlet, useParams } from 'react-router'
import { Card, EmptyState, LinkButton } from '@/shared/ui'
import { useSeller } from './useSeller'

/** Пускает в /seller/shops/:shopId/* только если магазин принадлежит продавцу. */
export function ShopRoute() {
  const { shopId } = useParams()
  const { profile } = useSeller()

  if (!profile.shops.some((shop) => String(shop.id) === shopId)) {
    return (
      <Card>
        <EmptyState
          title="Магазин не найден"
          text="Возможно, ссылка устарела или магазин принадлежит другому продавцу."
          action={<LinkButton to="/seller">В кабинет</LinkButton>}
        />
      </Card>
    )
  }

  return <Outlet />
}
