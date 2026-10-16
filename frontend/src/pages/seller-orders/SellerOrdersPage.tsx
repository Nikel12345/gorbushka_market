import { useCallback } from 'react'
import { useSearchParams } from 'react-router'
import { useSeller } from '@/features/seller'
import { ApiError, getErrorMessage, sellerApi, type Order, type OrderStatus, type Shop } from '@/shared/api'
import { parsePage, updateSearchParams, useRequest } from '@/shared/lib'
import {
  Card,
  EmptyState,
  ErrorState,
  LinearProgress,
  LinkButton,
  Loader,
  PageHeader,
  Pagination,
  Tabs,
  type TabItem,
} from '@/shared/ui'
import { SellerOrderCard } from './SellerOrderCard'
import './SellerOrdersPage.css'

type StatusFilter = OrderStatus | 'all'

// Вкладки — по шагам работы: что подтвердить, что собрать, что ждёт выдачи
const STATUS_TABS: TabItem<StatusFilter>[] = [
  { value: 'all', label: 'Все' },
  { value: 'new', label: 'Новые' },
  { value: 'confirmed', label: 'Собрать' },
  { value: 'ready', label: 'Ждут выдачи' },
  { value: 'completed', label: 'Выполненные' },
  { value: 'cancelled', label: 'Отменённые' },
]

const EMPTY_TEXT: Record<StatusFilter, string> = {
  all: 'Здесь появятся заказы покупателей вашего магазина.',
  new: 'Новых заказов нет — все подтверждены.',
  confirmed: 'Собирать нечего.',
  ready: 'Нет заказов, которые ждут покупателя или курьера.',
  completed: 'Выполненных заказов пока нет.',
  cancelled: 'Отменённых заказов нет.',
}

function parseStatus(value: string | null): StatusFilter {
  return STATUS_TABS.some((tab) => tab.value === value) ? (value as StatusFilter) : 'all'
}

/**
 * /seller/orders — обработка заказов. API отдаёт заказы по одному магазину,
 * поэтому магазин выбирается на странице (?shop=), по умолчанию — текущий.
 */
export function SellerOrdersPage() {
  const { shops, activeShopId } = useSeller()
  const [searchParams] = useSearchParams()
  const shop =
    shops.find((item) => String(item.id) === searchParams.get('shop')) ??
    shops.find((item) => item.id === activeShopId)

  if (!shop) {
    return (
      <>
        <PageHeader title="Заказы" />
        <Card>
          <EmptyState
            title="Магазинов пока нет"
            text="Заказы появятся, когда покупатели начнут покупать товары вашего магазина."
            action={
              <LinkButton variant="primary" to="/seller/shops/new">
                Создать магазин
              </LinkButton>
            }
          />
        </Card>
      </>
    )
  }

  return <ShopOrders shop={shop} />
}

function ShopOrders({ shop }: { shop: Shop }) {
  const { shops } = useSeller()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const status = parseStatus(searchParams.get('status'))

  const load = useCallback(
    (signal: AbortSignal) =>
      sellerApi.listOrders(shop.id, { page, status: status === 'all' ? undefined : status }, { signal }),
    [shop.id, page, status],
  )
  const orders = useRequest(load)
  const { mutate } = orders

  // Заказ после смены статуса остаётся на месте (даже если уже не подходит под вкладку),
  // чтобы список не прыгал под рукой
  const replaceOrder = useCallback(
    (updated: Order) =>
      mutate((data) => ({
        ...data,
        results: data.results.map((order) => (order.id === updated.id ? updated : order)),
      })),
    [mutate],
  )

  function changeStatus(next: StatusFilter) {
    setSearchParams((prev) => updateSearchParams(prev, { status: next === 'all' ? null : next, page: null }))
  }

  function changeShop(shopId: string) {
    setSearchParams((prev) => updateSearchParams(prev, { shop: shopId, page: null }))
  }

  function goToPage(next: number) {
    setSearchParams((prev) => updateSearchParams(prev, { page: next > 1 ? next : null }))
  }

  let content
  if (orders.status === 'error') {
    const pageMissing = orders.error instanceof ApiError && orders.error.status === 404 && page > 1
    content = (
      <Card>
        {pageMissing ? (
          <EmptyState
            title="Такой страницы нет"
            action={
              <LinkButton to={{ search: `?${updateSearchParams(searchParams, { page: null })}` }}>
                К первой странице
              </LinkButton>
            }
          />
        ) : (
          <ErrorState message={getErrorMessage(orders.error)} onRetry={orders.reload} />
        )}
      </Card>
    )
  } else if (!orders.data) {
    content = <Loader />
  } else if (orders.data.results.length === 0) {
    content = (
      <Card>
        <EmptyState title="Заказов нет" text={EMPTY_TEXT[status]} />
      </Card>
    )
  } else {
    content = (
      <ul className={orders.status === 'loading' ? 'seller-orders seller-orders--dimmed' : 'seller-orders'}>
        {orders.data.results.map((order) => (
          <li key={order.id}>
            <SellerOrderCard shopId={shop.id} order={order} onChange={replaceOrder} />
          </li>
        ))}
      </ul>
    )
  }

  return (
    <>
      <PageHeader
        title="Заказы"
        subtitle={shops.length > 1 ? undefined : shop.name}
        actions={
          shops.length > 1 && (
            <label className="seller-orders__shop">
              <span className="ui-muted">Магазин</span>
              <select className="ui-input" value={shop.id} onChange={(event) => changeShop(event.target.value)}>
                {shops.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          )
        }
      />

      <Card flush>
        {orders.status === 'loading' && orders.data && <LinearProgress />}
        <Tabs label="Статус заказа" items={STATUS_TABS} value={status} onChange={changeStatus} />
      </Card>

      {content}

      {orders.status !== 'error' && orders.data && orders.data.results.length > 0 && (
        <Pagination
          page={page}
          total={orders.data.count}
          hasPrevious={Boolean(orders.data.previous)}
          hasNext={Boolean(orders.data.next)}
          disabled={orders.status === 'loading'}
          onChange={goToPage}
        />
      )}
    </>
  )
}
