import { useCallback } from 'react'
import { Link, useNavigationType } from 'react-router'
import { ORDER_STATUS_TONE, PAYMENT_STATUS_TONE } from '@/entities/order'
import { ProductImage } from '@/entities/product'
import { getErrorMessage, purchasesApi, type Purchase } from '@/shared/api'
import { formatDateTime, formatPrice, useCursorFeed } from '@/shared/lib'
import { Button, Chip, EmptyState, ErrorState, InfiniteScrollTrigger, LinkButton, Loader } from '@/shared/ui'
import './OrdersPage.css'

/**
 * Заказы покупателя: /orders. Одна карточка — одна покупка (оформлена одной кнопкой),
 * внутри — части по магазинам со своими статусами. Клик — подробности.
 */
export function OrdersPage() {
  const navigationType = useNavigationType()
  const load = useCallback(
    (cursor: string | undefined, signal: AbortSignal) => purchasesApi.list({ cursor }, { signal }),
    [],
  )
  // «Назад» из подробностей — та же лента и то же место
  const feed = useCursorFeed(load, { key: 'purchases', restore: navigationType === 'POP' })

  let content
  if (feed.failed === 'replace') {
    content = <ErrorState message={getErrorMessage(feed.error)} onRetry={feed.retry} />
  } else if (feed.initial) {
    content = <Loader />
  } else if (feed.items.length === 0) {
    content = (
      <EmptyState
        title="Заказов пока нет"
        text="Оформленные заказы появятся здесь."
        action={
          <LinkButton variant="primary" to="/">
            Перейти к покупкам
          </LinkButton>
        }
      />
    )
  } else {
    content = (
      <>
        <ul className="orders-list">
          {feed.items.map((purchase) => (
            <li key={purchase.id}>
              <PurchaseCard purchase={purchase} />
            </li>
          ))}
        </ul>
        <InfiniteScrollTrigger
          onReach={feed.loadMore}
          disabled={!feed.hasMore || feed.loading !== null || feed.failed !== null}
        />
        <div className="orders-list__footer">
          {feed.loading === 'more' && <Loader label="Загружаем ещё…" />}
          {feed.failed === 'more' && (
            <div role="alert">
              Не удалось загрузить заказы: {getErrorMessage(feed.error)} <Button onClick={feed.retry}>Повторить</Button>
            </div>
          )}
        </div>
      </>
    )
  }

  return (
    <>
      <h1 className="orders-page__title">Мои заказы</h1>
      {content}
    </>
  )
}

function PurchaseCard({ purchase }: { purchase: Purchase }) {
  return (
    <Link to={`/orders/${purchase.id}`} className="purchase-card">
      <div className="purchase-card__head">
        <span className="purchase-card__number">Заказ №{purchase.id}</span>
        <span className="purchase-card__date">от {formatDateTime(purchase.created_at)}</span>
        <span className="purchase-card__total">{formatPrice(purchase.total_amount)}</span>
      </div>

      <ul className="purchase-card__orders">
        {purchase.orders.map((order) => (
          <li key={order.id} className="purchase-card__order">
            <span className="purchase-card__shop">{order.shop.name}</span>
            <Chip tone={ORDER_STATUS_TONE[order.status]}>{order.status_display}</Chip>
            <ul className="purchase-card__thumbs">
              {order.items.map((item) => (
                <li key={item.id} title={`${item.title} × ${item.quantity}`}>
                  <ProductImage src={item.image} alt={item.title} className="purchase-card__thumb" />
                  {item.quantity > 1 && <span className="purchase-card__qty">×{item.quantity}</span>}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>

      <div className="purchase-card__foot">
        <span className="ui-muted">{purchase.payment_method_display}</span>
        <Chip tone={PAYMENT_STATUS_TONE[purchase.payment_status]}>{purchase.payment_status_display}</Chip>
        <span className="purchase-card__more">Подробнее ›</span>
      </div>
    </Link>
  )
}
