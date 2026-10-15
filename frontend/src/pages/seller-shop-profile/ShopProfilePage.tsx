import { useCallback } from 'react'
import { Link } from 'react-router'
import { ShopForm, useCurrentShop, useSeller } from '@/features/seller'
import { sellerApi, type ShopPayload } from '@/shared/api'
import { formatDate, pluralize, useRequest } from '@/shared/lib'
import { Card, PageHeader } from '@/shared/ui'

const PRODUCT_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']

/** /seller/shops/:shopId/profile — название, адрес и описание магазина. */
export function ShopProfilePage() {
  const shop = useCurrentShop()
  const { updateShop } = useSeller()

  // Счётчик товаров меняется при добавлении и снятии — берём свежий
  const load = useCallback((signal: AbortSignal) => sellerApi.getShop(shop.id, { signal }), [shop.id])
  const details = useRequest(load)
  const productsCount = details.data?.products_count ?? shop.products_count

  async function handleSubmit(payload: ShopPayload) {
    updateShop(await sellerApi.updateShop(shop.id, payload))
  }

  return (
    <>
      <PageHeader title={shop.name} subtitle="Профиль магазина" />

      <Card title="Основное">
        {/* key: другой магазин — форма с его данными */}
        <ShopForm
          key={shop.id}
          initial={{ name: shop.name, address: shop.address, description: shop.description }}
          submitLabel="Сохранить"
          submittingLabel="Сохраняем…"
          successMessage="Сохранено"
          onSubmit={handleSubmit}
        />
      </Card>

      <Card title="Сводка">
        <dl className="ui-props">
          <dt>На продаже</dt>
          <dd>
            <Link to={`/seller/shops/${shop.id}/products`}>{pluralize(productsCount, PRODUCT_WORDS)}</Link>
          </dd>
          <dt>Самовывоз</dt>
          <dd>{shop.address ? 'доступен' : <span className="ui-muted">недоступен — не указан адрес</span>}</dd>
          <dt>Магазин создан</dt>
          <dd>{formatDate(shop.created_at)}</dd>
          <dt>Номер</dt>
          <dd>{shop.id}</dd>
        </dl>
      </Card>
    </>
  )
}
