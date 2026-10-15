import { useNavigate } from 'react-router'
import { ShopForm, useSeller } from '@/features/seller'
import { sellerApi, type ShopPayload } from '@/shared/api'
import { Card, PageHeader } from '@/shared/ui'

/** /seller/shops/new — новый магазин. Для продавца без магазинов это первая страница кабинета. */
export function ShopCreatePage() {
  const { shops, addShop } = useSeller()
  const navigate = useNavigate()
  const first = shops.length === 0

  async function handleSubmit(payload: ShopPayload) {
    const shop = await sellerApi.createShop(payload)
    addShop(shop)
    navigate(`/seller/shops/${shop.id}/products`, { replace: true })
  }

  return (
    <>
      <PageHeader
        title={first ? 'Добро пожаловать' : 'Новый магазин'}
        subtitle={
          first
            ? 'Чтобы начать продавать, создайте магазин.'
            : 'Товары и заказы у каждого магазина свои.'
        }
      />
      <Card title={first ? 'Новый магазин' : undefined}>
        <ShopForm submitLabel="Создать магазин" submittingLabel="Создаём…" onSubmit={handleSubmit} />
      </Card>
    </>
  )
}
