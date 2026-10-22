import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { formatDeliveryPrice, formatDeliveryTerms } from '@/entities/delivery'
import { ProductImage } from '@/entities/product'
import {
  ApiError,
  checkoutApi,
  getErrorMessage,
  getFieldErrors,
  type CheckoutItem,
  type CheckoutPreview,
  type DeliveryChoice,
  type DeliveryMethod,
  type FieldErrors,
  type PaymentMethodCode,
  type Purchase,
} from '@/shared/api'
import { formatPrice, pluralize, useRequest } from '@/shared/lib'
import { Button, Field, FieldError, LinearProgress, OrderSummary, Switch } from '@/shared/ui'
import { SlotPicker, type SlotValue } from './SlotPicker'

const FORM_ID = 'checkout-form'
const ITEM_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']
const slotErrorKey = (methodId: number) => `slot_${methodId}`

interface CheckoutFormProps {
  preview: CheckoutPreview
  /** Корзина или цены изменились — перечитать страницу оформления */
  onStale: () => void
  onPlaced: (purchase: Purchase) => void
}

/**
 * Способ получения выбирается у каждой позиции; сервер (quote) объединяет позиции
 * в отправки и считает доставку. Время — одно на способ, адрес — один на покупку.
 */
export function CheckoutForm({ preview, onStale, onPlaced }: CheckoutFormProps) {
  const methodById = useMemo(
    () => new Map(preview.items.flatMap((item) => item.delivery_methods).map((method) => [method.id, method])),
    [preview],
  )

  // --- Способы получения и расчёт ---

  /** Что покупатель выбрал руками; остальным позициям — первый доступный способ */
  const [picked, setPicked] = useState<Record<number, number>>({})
  const [useBonus, setUseBonus] = useState(false)
  const choices = resolveChoices(preview.items, picked)
  const methodOf = (productId: number) =>
    methodById.get(choices.find((choice) => choice.product_id === productId)!.delivery_method_id)!

  // От preview, а не только от выбора: после перечитывания корзины пересчитываем и при тех же способах
  const loadPlan = useCallback(
    (signal: AbortSignal) => checkoutApi.quote(resolveChoices(preview.items, picked), useBonus, { signal }),
    [preview, picked, useBonus],
  )
  const plan = useRequest(loadPlan)
  const planReady = plan.status === 'success'

  const planConflict = plan.error instanceof ApiError && plan.error.status === 409
  useEffect(() => {
    if (planConflict) onStale()
  }, [planConflict, onStale])

  const shipments = plan.data?.shipments ?? []
  const shipmentMethods = shipments.map((shipment) => methodById.get(shipment.delivery_method.id)!)
  // Время выбирается одно на способ — даже если по нему несколько отправок
  const slotMethods = [...new Map(shipmentMethods.filter((m) => m.has_slots).map((m) => [m.id, m])).values()]
  const needsAddress = shipmentMethods.some((method) => method.requires_address)

  // --- Остальные поля ---

  const [slots, setSlots] = useState<Record<number, SlotValue>>({})
  const [address, setAddress] = useState('')
  const [payment, setPayment] = useState<PaymentMethodCode>(() =>
    preview.payment_methods.some((m) => m.code === 'on_delivery') ? 'on_delivery' : preview.payment_methods[0].code,
  )
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [placing, setPlacing] = useState(false)

  const toPay = plan.data?.amount_to_pay
  const bonusUsed = plan.data ? Number(plan.data.bonus_amount) : 0
  const balanceShort = toPay !== undefined ? Number(toPay) - Number(preview.balance) : 0
  const hasBonus = Number(preview.bonus) > 0
  const bonusSharePercent = Math.round(Number(preview.bonus_max_share) * 100)

  function validate(): FieldErrors {
    const result: FieldErrors = {}
    for (const method of slotMethods) {
      if (!slots[method.id]) result[slotErrorKey(method.id)] = ['Выберите время доставки.']
    }
    if (needsAddress && !address.trim()) result.address = ['Укажите адрес доставки.']
    if (payment === 'balance' && balanceShort > 0) {
      result.payment_method = [`На балансе не хватает ${formatPrice(balanceShort)}.`]
    }
    return result
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (plan.status !== 'success' || placing) return
    const localErrors = validate()
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setPlacing(true)
    try {
      const purchase = await checkoutApi.place({
        items: choices,
        slots: slotMethods.map((method) => ({ delivery_method_id: method.id, ...slots[method.id] })),
        address: needsAddress ? address.trim() : undefined,
        payment_method: payment,
        comment: comment.trim() || undefined,
        use_bonus: useBonus,
        // Сервер сверяет итог до бонусов
        expected_total: plan.data.total_amount,
      })
      onPlaced(purchase)
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        // Корзина или сумма изменились: показываем причину и перечитываем
        setErrors({ non_field_errors: [getErrorMessage(error)] })
        onStale()
      } else {
        setErrors(getFieldErrors(error))
      }
      setPlacing(false)
    }
  }

  const itemsCount = preview.items.reduce((sum, item) => sum + item.quantity, 0)
  const unavailableCount = preview.unavailable_items.length

  return (
    <form id={FORM_ID} onSubmit={handleSubmit} noValidate>
      <h1 className="checkout__title">Оформление заказа</h1>

      <div className="checkout">
        <div className="checkout__main">
          {unavailableCount > 0 && (
            <section className="checkout-section checkout-section--warning">
              <h2 className="checkout-section__title">Не войдут в заказ</h2>
              <p className="checkout-section__hint">Эти товары останутся в корзине.</p>
              <ul className="checkout-unavailable">
                {preview.unavailable_items.map((item) => (
                  <li key={item.product.id}>
                    <Link to={`/products/${item.product.id}`}>{item.product.title}</Link>
                    <span className="checkout-unavailable__reason">{item.problem.detail}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="checkout-section">
            <h2 className="checkout-section__title">Товары и способ получения</h2>
            <ul className="checkout-items">
              {preview.items.map((item) => (
                <CheckoutItemRow
                  key={item.product.id}
                  item={item}
                  method={methodOf(item.product.id)}
                  onPick={(methodId) => setPicked((prev) => ({ ...prev, [item.product.id]: methodId }))}
                />
              ))}
            </ul>
          </section>

          <section className="checkout-section">
            <h2 className="checkout-section__title">Доставка</h2>
            {plan.status === 'loading' && <LinearProgress />}
            {plan.status === 'error' && !planConflict && (
              <FieldError messages={[getErrorMessage(plan.error)]} />
            )}
            <ul className="checkout-shipments">
              {shipments.map((shipment, index) => {
                const method = shipmentMethods[index]
                const titles = shipment.product_ids.map(
                  (id) => preview.items.find((item) => item.product.id === id)?.product.title,
                )
                const pickupAddress =
                  shipment.shop &&
                  preview.items.find((item) => item.product.shop.id === shipment.shop!.id)?.pickup_address
                // Время — у первой отправки этого способа
                const showSlots =
                  method.has_slots && shipmentMethods.findIndex((m) => m.id === method.id) === index
                return (
                  <li key={`${method.id}-${shipment.shop?.id ?? 'market'}`} className="checkout-shipment">
                    <div className="checkout-shipment__head">
                      <span className="checkout-shipment__name">{method.name}</span>
                      <span className="checkout-shipment__price">{formatDeliveryPrice(shipment.price)}</span>
                    </div>
                    <span className="checkout-shipment__items">{titles.join(', ')}</span>
                    {pickupAddress && <span className="checkout-shipment__address">Забрать: {pickupAddress}</span>}
                    {showSlots && (
                      <SlotPicker
                        method={method}
                        value={slots[method.id]}
                        onChange={(value) => setSlots((prev) => ({ ...prev, [method.id]: value }))}
                        errors={errors[slotErrorKey(method.id)]}
                      />
                    )}
                  </li>
                )
              })}
            </ul>

            {needsAddress && (
              <Field label="Адрес доставки" errors={errors.address}>
                <input
                  className="ui-input"
                  value={address}
                  onChange={(event) => setAddress(event.target.value)}
                  placeholder="Город, улица, дом, квартира"
                  maxLength={500}
                  autoComplete="street-address"
                  aria-invalid={Boolean(errors.address)}
                />
              </Field>
            )}
          </section>

          <section className="checkout-section">
            <h2 className="checkout-section__title">Оплата</h2>
            <div className="checkout-options" role="radiogroup" aria-label="Способ оплаты">
              {preview.payment_methods.map((method) => (
                <label key={method.code} className="checkout-option">
                  <input
                    type="radio"
                    name="payment"
                    checked={payment === method.code}
                    onChange={() => setPayment(method.code)}
                  />
                  <span className="checkout-option__name">{method.name}</span>
                  {method.code === 'balance' && (
                    <span className="checkout-option__terms">Деньги на балансе: {formatPrice(preview.balance)}</span>
                  )}
                </label>
              ))}
            </div>
            <FieldError messages={errors.payment_method} />

          </section>

          <section className="checkout-section">
            <Field label="Комментарий к заказу" errors={errors.comment}>
              <textarea
                className="ui-input"
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="Необязательно"
                maxLength={1000}
              />
            </Field>
          </section>
        </div>

        {/* Баланс — общий на всю покупку, рядом с итогом */}
        <div className="checkout__side">
          <section className="checkout-wallet" aria-label="Баланс">
            <h2 className="checkout-wallet__title">Баланс</h2>
            <dl className="checkout-wallet__amounts">
              <div>
                <dt>Всего</dt>
                <dd>{formatPrice(Number(preview.balance) + Number(preview.bonus))}</dd>
              </div>
              <div>
                <dt>Бонусы</dt>
                <dd>{formatPrice(preview.bonus)}</dd>
              </div>
            </dl>
            <Switch checked={useBonus} onChange={setUseBonus} disabled={!hasBonus}>
              Оплатить бонусами
            </Switch>
            <span className="checkout-wallet__hint">
              {!hasBonus
                ? 'Бонусов пока нет.'
                : useBonus && bonusUsed > 0
                  ? `Спишется ${formatPrice(bonusUsed)} — остальное выбранным способом.`
                  : `Бонусами можно оплатить до ${bonusSharePercent}% заказа.`}
            </span>
          </section>
          <OrderSummary
            title="Ваш заказ"
            rows={[
              {
                label: `Товары, ${pluralize(itemsCount, ITEM_WORDS)}`,
                value: formatPrice(plan.data?.items_total ?? preview.items_total),
              },
              { label: 'Доставка', value: plan.data ? formatDeliveryPrice(plan.data.delivery_total) : '…' },
              ...(bonusUsed > 0 ? [{ label: 'Бонусами', value: `−${formatPrice(bonusUsed)}` }] : []),
            ]}
            total={toPay !== undefined ? formatPrice(toPay) : '…'}
          >
            {unavailableCount > 0 && (
              <p className="ui-summary__note">
                {pluralize(unavailableCount, ITEM_WORDS)} не войдут в заказ и останутся в корзине.
              </p>
            )}
            <FieldError messages={errors.non_field_errors} />
            <Button
              type="submit"
              form={FORM_ID}
              variant="primary"
              className="ui-summary__action"
              disabled={!planReady || placing}
            >
              {placing ? 'Оформляем…' : 'Оформить заказ'}
            </Button>
          </OrderSummary>
        </div>
      </div>
    </form>
  )
}

/** Способ у каждой позиции: выбранный покупателем, если он ещё доступен, иначе первый */
function resolveChoices(items: CheckoutItem[], picked: Record<number, number>): DeliveryChoice[] {
  return items.map((item) => {
    const pickedId = picked[item.product.id]
    const valid = item.delivery_methods.some((method) => method.id === pickedId)
    return { product_id: item.product.id, delivery_method_id: valid ? pickedId : item.delivery_methods[0].id }
  })
}

interface CheckoutItemRowProps {
  item: CheckoutItem
  method: DeliveryMethod
  onPick: (methodId: number) => void
}

function CheckoutItemRow({ item, method, onPick }: CheckoutItemRowProps) {
  const { product } = item
  return (
    <li className="checkout-item">
      <Link to={`/products/${product.id}`} className="checkout-item__image" tabIndex={-1} aria-hidden="true">
        <ProductImage src={product.image} alt="" />
      </Link>
      <div className="checkout-item__info">
        <Link to={`/products/${product.id}`} className="checkout-item__title">
          {product.title}
        </Link>
        <span className="checkout-item__meta">
          {item.quantity} шт. × {formatPrice(product.price)}
        </span>
        <div className="checkout-options" role="radiogroup" aria-label="Способ получения">
          {item.delivery_methods.map((option) => (
            <label key={option.id} className="checkout-option">
              <input
                type="radio"
                name={`delivery-${product.id}`}
                checked={option.id === method.id}
                onChange={() => onPick(option.id)}
              />
              <span className="checkout-option__name">{option.name}</span>
              <span className="checkout-option__terms">{formatDeliveryTerms(option)}</span>
            </label>
          ))}
        </div>
      </div>
      <span className="checkout-item__total">{formatPrice(item.total)}</span>
    </li>
  )
}
