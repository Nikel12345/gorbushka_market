import { useCallback } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { formatDeliveryPrice, formatSlot } from '@/entities/delivery'
import { ORDER_STATUS_TONE, PAYMENT_STATUS_TONE } from '@/entities/order'
import { ProductImage } from '@/entities/product'
import { ApiError, getErrorMessage, purchasesApi, type BuyerOrder, type Shipment } from '@/shared/api'
import { formatDateTime, formatPrice, useRequest } from '@/shared/lib'
import { Chip, EmptyState, ErrorState, LinkButton, Loader, OrderSummary } from '@/shared/ui'
import './OrdersPage.css'

/** Подробности заказа покупателя: /orders/:purchaseId */
export function OrderDetailsPage() {
  const purchaseId = Number(useParams().purchaseId)
  const navigate = useNavigate()
  const location = useLocation()

  const load = useCallback((signal: AbortSignal) => purchasesApi.get(purchaseId, { signal }), [purchaseId])
  const purchase = useRequest(load)

  // Пришли из списка — возвращаемся на то же место; открыли по ссылке — к списку
  const back =
    location.key !== 'default' ? (
      <button type="button" className="orders-page__back" onClick={() => navigate(-1)}>
        ← Мои заказы
      </button>
    ) : (
      <Link to="/orders" className="orders-page__back">
        ← Мои заказы
      </Link>
    )

  if (purchase.status === 'error') {
    const notFound = purchase.error instanceof ApiError && purchase.error.status === 404
    return (
      <>
        {back}
        {notFound ? (
          <EmptyState title="Заказ не найден" action={<LinkButton to="/orders">Все заказы</LinkButton>} />
        ) : (
          <ErrorState message={getErrorMessage(purchase.error)} onRetry={purchase.reload} />
        )}
      </>
    )
  }

  if (!purchase.data || purchase.data.id !== purchaseId) {
    return (
      <>
        {back}
        <Loader />
      </>
    )
  }

  const p = purchase.data

  return (
    <>
      {back}
      <header className="order-details__head">
        <h1 className="orders-page__title">Заказ №{p.id}</h1>
        <span className="ui-muted">от {formatDateTime(p.created_at)}</span>
      </header>

      <div className="order-details">
        <div className="order-details__main">
          {p.orders.map((order) => (
            <OrderPart key={order.id} order={order} />
          ))}

          <section className="order-section">
            <h2 className="order-section__title">Получение</h2>
            <ul className="order-shipments">
              {p.shipments.map((shipment) => (
                <ShipmentRow key={shipment.id} shipment={shipment} orders={p.orders} />
              ))}
            </ul>
          </section>

          {p.comment && (
            <section className="order-section">
              <h2 className="order-section__title">Комментарий</h2>
              <p className="order-section__text">{p.comment}</p>
            </section>
          )}
        </div>

        <OrderSummary
          title="Оплата"
          rows={[
            { label: 'Товары', value: formatPrice(p.items_total) },
            { label: 'Доставка', value: formatDeliveryPrice(p.delivery_total) },
            ...(Number(p.bonus_amount) > 0 ? [{ label: 'Бонусами', value: `−${formatPrice(p.bonus_amount)}` }] : []),
          ]}
          total={formatPrice(Number(p.total_amount) - Number(p.bonus_amount))}
        >
          <dl className="order-payment">
            <dt>Способ оплаты</dt>
            <dd>{p.payment_method_display}</dd>
            <dt>Статус</dt>
            <dd>
              <Chip tone={PAYMENT_STATUS_TONE[p.payment_status]}>{p.payment_status_display}</Chip>
            </dd>
          </dl>
        </OrderSummary>
      </div>
    </>
  )
}

/** Часть заказа со своим статусом и позициями. Обычно одна; несколько — у заказов времён маркетплейса. */
function OrderPart({ order }: { order: BuyerOrder }) {
  return (
    <section className="order-section">
      <div className="order-section__head">
        <h2 className="order-section__title">Товары</h2>
        <Chip tone={ORDER_STATUS_TONE[order.status]}>{order.status_display}</Chip>
      </div>
      <span className="order-section__meta">Обновлён {formatDateTime(order.updated_at)}</span>

      <ul className="order-items">
        {order.items.map((item) => (
          <li key={item.id} className="order-item">
            <Link to={`/products/${item.product_id}`} className="order-item__image" tabIndex={-1} aria-hidden="true">
              <ProductImage src={item.image} alt="" />
            </Link>
            <div className="order-item__info">
              <Link to={`/products/${item.product_id}`} className="order-item__title">
                {item.title}
              </Link>
              <span className="order-item__meta">
                {item.quantity} шт. × {formatPrice(item.price)}
                {item.shipment && ` · ${item.shipment.delivery_method.name}`}
              </span>
            </div>
            <span className="order-item__total">{formatPrice(item.total)}</span>
          </li>
        ))}
      </ul>
      <div className="order-section__total">
        <span>Сумма</span>
        <span>{formatPrice(order.total_amount)}</span>
      </div>
    </section>
  )
}

/** Отправка: способ, время, адрес и что в ней едет */
function ShipmentRow({ shipment, orders }: { shipment: Shipment; orders: BuyerOrder[] }) {
  const items = orders.flatMap((order) => order.items).filter((item) => item.shipment?.id === shipment.id)
  const isPickup = shipment.delivery_method.kind === 'pickup'

  return (
    <li className="order-shipment">
      <div className="order-shipment__head">
        <span className="order-shipment__name">{shipment.delivery_method.name}</span>
        <span>{formatDeliveryPrice(shipment.price)}</span>
      </div>
      <dl className="order-shipment__props">
        {shipment.address && (
          <>
            <dt>{isPickup ? 'Где забрать' : 'Адрес'}</dt>
            <dd>{shipment.address}</dd>
          </>
        )}
        {shipment.slot && (
          <>
            <dt>Время</dt>
            <dd>{formatSlot(shipment.slot)}</dd>
          </>
        )}
        <dt>Товары</dt>
        <dd>{items.map((item) => `${item.title} × ${item.quantity}`).join(', ')}</dd>
      </dl>
    </li>
  )
}
