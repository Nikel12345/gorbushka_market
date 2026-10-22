import { formatDeliveryPrice, formatSlot } from '@/entities/delivery'
import type { Purchase } from '@/shared/api'
import { formatPrice } from '@/shared/lib'
import { LinkButton } from '@/shared/ui'

/** Покупка оформлена: номер, сумма, как и когда получать. */
export function CheckoutSuccess({ purchase }: { purchase: Purchase }) {
  const items = purchase.orders.flatMap((order) => order.items)

  return (
    <section className="checkout-success">
      <span className="checkout-success__icon" aria-hidden="true">
        ✓
      </span>
      <h1 className="checkout-success__title">Заказ оформлен</h1>
      <p className="checkout-success__lead">
        Заказ №{purchase.id} на {formatPrice(purchase.total_amount)} · {purchase.payment_method_display},{' '}
        {purchase.payment_status_display.toLowerCase()}
      </p>

      <ul className="checkout-success__list">
        {purchase.shipments.map((shipment) => (
          <li key={shipment.id} className="checkout-shipment">
            <div className="checkout-shipment__head">
              <span className="checkout-shipment__name">{shipment.delivery_method.name}</span>
              <span className="checkout-shipment__price">{formatDeliveryPrice(shipment.price)}</span>
            </div>
            {shipment.slot && <span>{formatSlot(shipment.slot)}</span>}
            {shipment.address && <span className="checkout-shipment__address">{shipment.address}</span>}
            <span className="checkout-shipment__items">
              {items
                .filter((item) => item.shipment?.id === shipment.id)
                .map((item) => `${item.title} × ${item.quantity}`)
                .join(', ')}
            </span>
          </li>
        ))}
      </ul>

      <div className="checkout-success__actions">
        <LinkButton to="/orders">Мои заказы</LinkButton>
        <LinkButton to="/" variant="primary">
          Продолжить покупки
        </LinkButton>
      </div>
    </section>
  )
}
