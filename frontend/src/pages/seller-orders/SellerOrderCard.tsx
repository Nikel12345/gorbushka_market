import { useState } from 'react'
import { formatSlot } from '@/entities/delivery'
import {
  ORDER_STATUS_TONE,
  PAYMENT_STATUS_TONE,
  orderProvider,
  orderSteps,
  statusActionLabel,
} from '@/entities/order'
import { ProductImage } from '@/entities/product'
import { getErrorMessage, sellerApi, type Order, type OrderStatusOption } from '@/shared/api'
import { formatDateTime, formatPersonName, formatPrice } from '@/shared/lib'
import { Button, Chip, FieldError } from '@/shared/ui'

interface SellerOrderCardProps {
  shopId: number
  order: Order
  onChange: (order: Order) => void
}

/** Подсказка продавцу: что сделать с заказом сейчас */
function nextStepHint(order: Order): string | null {
  const pickup = orderProvider(order) === 'shop'
  switch (order.status) {
    case 'new':
      return 'Проверьте наличие и подтвердите заказ.'
    case 'confirmed':
      return pickup ? 'Соберите заказ и отметьте, когда он будет готов к выдаче.' : 'Соберите заказ и передайте курьеру маркета.'
    case 'ready':
      return pickup ? 'Ждёт покупателя в павильоне.' : 'Заказ у курьера маркета — доставку отметит маркет.'
    default:
      return null
  }
}

/** Заказ в кабинете: доставка, оплата, товары, покупатель и кнопки следующего шага. */
export function SellerOrderCard({ shopId, order, onChange }: SellerOrderCardProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [confirmCancel, setConfirmCancel] = useState(false)

  const pickup = orderProvider(order) === 'shop'
  const forward = order.available_statuses.filter((option) => option.status !== 'cancelled')
  const cancel = order.available_statuses.find((option) => option.status === 'cancelled')
  // Самовывоз с оплатой при получении — деньги (за вычетом бонусов) берёт продавец
  const amountDue = Number(order.amount_due)
  const collectPayment = pickup && amountDue > 0 && order.payment?.status === 'unpaid' && order.status !== 'cancelled'

  async function apply(option: OrderStatusOption) {
    setBusy(true)
    setError(undefined)
    try {
      onChange(await sellerApi.changeOrderStatus(shopId, order.id, option.status))
      setConfirmCancel(false)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const hint = nextStepHint(order)
  const buyerName = formatPersonName(order.buyer)

  return (
    <article className={`seller-order seller-order--${order.status}`}>
      <header className="seller-order__head">
        <div className="seller-order__title">
          <span className="seller-order__number">№ {order.id}</span>
          <span className="ui-muted">{formatDateTime(order.created_at)}</span>
          {order.purchase_id && <span className="ui-muted">· покупка №{order.purchase_id}</span>}
        </div>
        <Chip tone={ORDER_STATUS_TONE[order.status]}>{order.status_display}</Chip>
      </header>

      <div className="seller-order__badges">
        <span className={`seller-order__badge seller-order__badge--${pickup ? 'pickup' : 'courier'}`}>
          {pickup ? <PickupIcon /> : <CourierIcon />}
          {order.shipment?.delivery_method.name ?? 'Самовывоз'}
          {order.shipment?.slot && <b>{formatSlot(order.shipment.slot)}</b>}
        </span>
        {order.payment && (
          <span className="seller-order__badge">
            {order.payment.method_display}
            <Chip tone={PAYMENT_STATUS_TONE[order.payment.status]}>{order.payment.status_display}</Chip>
          </span>
        )}
      </div>

      {order.status !== 'cancelled' && (
        <ol className="seller-order__steps" aria-label="Ход заказа">
          {orderSteps(order).map((step) => (
            <li
              key={step.status}
              className={step.done ? 'seller-order__step seller-order__step--done' : 'seller-order__step'}
              aria-current={step.status === order.status ? 'step' : undefined}
            >
              {step.label}
            </li>
          ))}
        </ol>
      )}

      <ul className="seller-order__items">
        {order.items.map((item) => (
          <li key={item.id} className="seller-order__item">
            <ProductImage src={item.image} alt="" className="seller-order__thumb" />
            <span className="seller-order__item-title">{item.title}</span>
            <span className="seller-order__item-qty">
              {item.quantity} × {formatPrice(item.price)}
            </span>
            <span className="seller-order__item-total">{formatPrice(item.total)}</span>
          </li>
        ))}
      </ul>

      <dl className="seller-order__info">
        <dt>Покупатель</dt>
        <dd>
          {buyerName}
          {buyerName !== order.buyer.email && (
            <>
              {' · '}
              <a href={`mailto:${order.buyer.email}`}>{order.buyer.email}</a>
            </>
          )}
        </dd>
        {order.comment && (
          <>
            <dt>Комментарий</dt>
            <dd className="seller-order__comment">{order.comment}</dd>
          </>
        )}
      </dl>

      <footer className="seller-order__foot">
        <div className="seller-order__summary">
          <span className="seller-order__total">{formatPrice(order.total_amount)}</span>
          {Number(order.bonus_amount) > 0 && (
            <span className="seller-order__hint">Бонусами оплачено {formatPrice(order.bonus_amount)}</span>
          )}
          {collectPayment && (
            <span className="seller-order__collect">Взять с покупателя при выдаче: {formatPrice(order.amount_due)}</span>
          )}
          {hint && <span className="seller-order__hint">{hint}</span>}
        </div>

        {confirmCancel && cancel ? (
          <div className="seller-order__actions">
            <span className="seller-order__confirm">Отменить заказ? Товары вернутся в продажу.</span>
            <Button variant="text" onClick={() => setConfirmCancel(false)} disabled={busy}>
              Нет
            </Button>
            <Button variant="danger" onClick={() => apply(cancel)} disabled={busy}>
              {busy ? 'Отменяем…' : 'Да, отменить'}
            </Button>
          </div>
        ) : (
          (forward.length > 0 || cancel) && (
            <div className="seller-order__actions">
              {cancel && (
                <Button variant="text" onClick={() => setConfirmCancel(true)} disabled={busy}>
                  {statusActionLabel(cancel)}
                </Button>
              )}
              {forward.map((option) => (
                <Button key={option.status} variant="primary" onClick={() => apply(option)} disabled={busy}>
                  {statusActionLabel(option)}
                </Button>
              ))}
            </div>
          )
        )}
      </footer>
      <FieldError messages={error ? [error] : undefined} />
    </article>
  )
}

function PickupIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-order__icon">
      <path d="M4 4h16l1 5a3 3 0 01-2 2.8V20H5v-8.2A3 3 0 013 9l1-5zm3 9v5h4v-5H7zm6 0v5h4v-5h-4zM5.6 6l-.6 3a1 1 0 002 0V6H5.6zM9 6v3a1 1 0 002 0V6H9zm4 0v3a1 1 0 002 0V6h-2zm4 0v3a1 1 0 002 0l-.6-3H17z" />
    </svg>
  )
}

function CourierIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-order__icon">
      <path d="M2 5h12v3h4l4 5v5h-2a3 3 0 01-6 0H9a3 3 0 01-6 0H2V5zm2 2v9h.8A3 3 0 019 16h3V7H4zm10 3v6h.8a3 3 0 014.4-.6V13.7L17 10h-3zM6 17a1 1 0 100 2 1 1 0 000-2zm11 0a1 1 0 100 2 1 1 0 000-2z" />
    </svg>
  )
}
