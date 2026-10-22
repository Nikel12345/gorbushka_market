import { Link } from 'react-router'
import { ShopForm, useSeller } from '@/features/seller'
import { adminApi, type ShopPayload } from '@/shared/api'
import { formatDate, pluralize, useRequest } from '@/shared/lib'
import { Card, PageHeader } from '@/shared/ui'

const PRODUCT_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']

const loadShop = (signal: AbortSignal) => adminApi.getShop({ signal })

/** /seller/shop — название, адрес и описание магазина. */
export function ShopProfilePage() {
  const { shop, updateShop } = useSeller()

  // Счётчик товаров меняется при добавлении и снятии — берём свежий
  const details = useRequest(loadShop)
  const productsCount = details.data?.products_count ?? shop.products_count

  async function handleSubmit(payload: ShopPayload) {
    updateShop(await adminApi.updateShop(payload))
  }

  return (
    <>
      <PageHeader title={shop.name} subtitle="Профиль магазина" />

      <Card title="Основное">
        <ShopForm
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
            <Link to="/seller/products">{pluralize(productsCount, PRODUCT_WORDS)}</Link>
          </dd>
          <dt>Самовывоз</dt>
          <dd>{shop.address ? 'доступен' : <span className="ui-muted">недоступен — не указан адрес</span>}</dd>
          <dt>Магазин создан</dt>
          <dd>{formatDate(shop.created_at)}</dd>
        </dl>
      </Card>
    </>
  )
}
