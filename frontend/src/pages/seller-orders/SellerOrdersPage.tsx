import { Fragment, useCallback, useState } from 'react'
import { useSearchParams } from 'react-router'
import { useSeller } from '@/features/seller'
import { ApiError, getErrorMessage, sellerApi, type Order, type OrderStatus, type Shop } from '@/shared/api'
import {
  formatDateTime,
  formatPersonName,
  formatPrice,
  parsePage,
  updateSearchParams,
  useRequest,
} from '@/shared/lib'
import {
  Card,
  Chip,
  EmptyState,
  ErrorState,
  LinearProgress,
  LinkButton,
  Loader,
  PageHeader,
  Pagination,
  Tabs,
  type ChipTone,
  type TabItem,
} from '@/shared/ui'
import './SellerOrdersPage.css'

type StatusFilter = OrderStatus | 'all'

const STATUS_TABS: TabItem<StatusFilter>[] = [
  { value: 'all', label: 'Все' },
  { value: 'new', label: 'Новые' },
  { value: 'confirmed', label: 'Подтверждённые' },
  { value: 'completed', label: 'Выполненные' },
  { value: 'cancelled', label: 'Отменённые' },
]

const STATUS_TONE: Record<OrderStatus, ChipTone> = {
  new: 'info',
  confirmed: 'warning',
  completed: 'success',
  cancelled: 'neutral',
}

const COLUMNS_COUNT = 6

function parseStatus(value: string | null): StatusFilter {
  return STATUS_TABS.some((tab) => tab.value === value) ? (value as StatusFilter) : 'all'
}

function countItems(order: Order): number {
  return order.items.reduce((sum, item) => sum + item.quantity, 0)
}

/**
 * /seller/orders — общий раздел заказов. API отдаёт заказы по одному магазину,
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
        <PageHeader title="История заказов" />
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
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(new Set())

  const load = useCallback(
    (signal: AbortSignal) =>
      sellerApi.listOrders(shop.id, { page, status: status === 'all' ? undefined : status }, { signal }),
    [shop.id, page, status],
  )
  const orders = useRequest(load)

  function changeStatus(next: StatusFilter) {
    setSearchParams((prev) => updateSearchParams(prev, { status: next === 'all' ? null : next, page: null }))
  }

  function changeShop(shopId: string) {
    setSearchParams((prev) => updateSearchParams(prev, { shop: shopId, page: null }))
  }

  function goToPage(next: number) {
    setSearchParams((prev) => updateSearchParams(prev, { page: next > 1 ? next : null }))
  }

  function toggle(orderId: number) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(orderId)) next.delete(orderId)
      else next.add(orderId)
      return next
    })
  }

  let content
  if (orders.status === 'error') {
    const pageMissing = orders.error instanceof ApiError && orders.error.status === 404 && page > 1
    content = pageMissing ? (
      <EmptyState
        title="Такой страницы нет"
        action={<LinkButton to={{ search: `?${updateSearchParams(searchParams, { page: null })}` }}>К первой странице</LinkButton>}
      />
    ) : (
      <ErrorState message={getErrorMessage(orders.error)} onRetry={orders.reload} />
    )
  } else if (!orders.data) {
    content = <Loader />
  } else if (orders.data.results.length === 0) {
    content =
      status === 'all' ? (
        <EmptyState title="Заказов пока нет" text="Здесь появятся заказы покупателей вашего магазина." />
      ) : (
        <EmptyState title="Нет заказов с таким статусом" />
      )
  } else {
    content = (
      <div className="ui-table-wrap">
        <table className="ui-table orders">
          <thead>
            <tr>
              <th>Заказ</th>
              <th>Дата</th>
              <th>Покупатель</th>
              <th className="ui-table__num">Товаров</th>
              <th className="ui-table__num">Сумма</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {orders.data.results.map((order) => {
              const isOpen = expanded.has(order.id)
              return (
                <Fragment key={order.id}>
                  <tr
                    className={`ui-table__row--clickable${isOpen ? ' ui-table__row--active' : ''}`}
                    onClick={() => toggle(order.id)}
                  >
                    <td>
                      <button
                        type="button"
                        className="orders__toggle"
                        aria-expanded={isOpen}
                        aria-controls={`order-${order.id}`}
                        onClick={(event) => {
                          event.stopPropagation()
                          toggle(order.id)
                        }}
                      >
                        <span className="orders__chevron" aria-hidden="true">
                          ▸
                        </span>
                        № {order.id}
                      </button>
                    </td>
                    <td className="orders__nowrap">{formatDateTime(order.created_at)}</td>
                    <td>{formatPersonName(order.buyer)}</td>
                    <td className="ui-table__num">{countItems(order)}</td>
                    <td className="ui-table__num">{formatPrice(order.total_amount)}</td>
                    <td>
                      <Chip tone={STATUS_TONE[order.status]}>{order.status_display}</Chip>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr id={`order-${order.id}`} className="orders__details">
                      <td colSpan={COLUMNS_COUNT}>
                        <OrderDetails order={order} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title="История заказов"
        subtitle={shops.length > 1 ? undefined : shop.name}
        actions={
          shops.length > 1 && (
            <label className="orders__shop">
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
        {content}
      </Card>

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

function OrderDetails({ order }: { order: Order }) {
  return (
    <div className="orders__details-body">
      <dl className="ui-props orders__meta">
        <dt>Покупатель</dt>
        <dd>
          {formatPersonName(order.buyer)}
          {formatPersonName(order.buyer) !== order.buyer.email && (
            <>
              {' · '}
              <a href={`mailto:${order.buyer.email}`}>{order.buyer.email}</a>
            </>
          )}
        </dd>
        <dt>Обновлён</dt>
        <dd>{formatDateTime(order.updated_at)}</dd>
      </dl>

      <table className="orders__items">
        <thead>
          <tr>
            <th>Товар</th>
            <th className="ui-table__num">Цена</th>
            <th className="ui-table__num">Кол-во</th>
            <th className="ui-table__num">Сумма</th>
          </tr>
        </thead>
        <tbody>
          {order.items.map((item) => (
            <tr key={item.id}>
              <td>{item.title}</td>
              <td className="ui-table__num">{formatPrice(item.price)}</td>
              <td className="ui-table__num">{item.quantity}</td>
              <td className="ui-table__num">{formatPrice(item.total)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>Итого</td>
            <td className="ui-table__num">{formatPrice(order.total_amount)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
