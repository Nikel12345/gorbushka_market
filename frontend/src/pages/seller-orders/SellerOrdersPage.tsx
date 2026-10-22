import { useCallback } from 'react'
import { useSearchParams } from 'react-router'
import { adminApi, ApiError, getErrorMessage, type Order, type OrderStatus } from '@/shared/api'
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
  all: 'Здесь появятся заказы покупателей.',
  new: 'Новых заказов нет — все подтверждены.',
  confirmed: 'Собирать нечего.',
  ready: 'Нет заказов, которые ждут покупателя или курьера.',
  completed: 'Выполненных заказов пока нет.',
  cancelled: 'Отменённых заказов нет.',
}

function parseStatus(value: string | null): StatusFilter {
  return STATUS_TABS.some((tab) => tab.value === value) ? (value as StatusFilter) : 'all'
}

/** /seller/orders — обработка заказов: вкладки по статусам, постраничный список. */
export function SellerOrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const status = parseStatus(searchParams.get('status'))

  const load = useCallback(
    (signal: AbortSignal) => adminApi.listOrders({ page, status: status === 'all' ? undefined : status }, { signal }),
    [page, status],
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
            <SellerOrderCard order={order} onChange={replaceOrder} />
          </li>
        ))}
      </ul>
    )
  }

  return (
    <>
      <PageHeader title="Заказы" />

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
