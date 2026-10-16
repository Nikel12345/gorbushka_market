import { Link } from 'react-router'
import { getErrorMessage, type Shop } from '@/shared/api'
import { Button, FieldError } from '@/shared/ui'
import { needsShopAddress, type DeliveryMethodsRequest } from './productForm'

interface DeliveryMethodsFieldProps {
  shop: Shop
  methods: DeliveryMethodsRequest
  value: number[]
  onChange: (ids: number[]) => void
  errors?: string[]
}

/**
 * Способы получения товара — чекбоксы из справочника маркета.
 * Самовывоз можно выбрать, только если у магазина указан адрес. Если он уже отмечен
 * (адрес стёрли позже) — снять отметку можно, поставить заново нельзя.
 */
export function DeliveryMethodsField({ shop, methods, value, onChange, errors }: DeliveryMethodsFieldProps) {
  function toggle(id: number, checked: boolean) {
    onChange(checked ? [...value, id] : value.filter((item) => item !== id))
  }

  let body
  if (methods.status === 'error') {
    body = (
      <div className="delivery-field__error">
        <span>Не удалось загрузить способы доставки: {getErrorMessage(methods.error)}</span>
        <Button onClick={methods.reload}>Повторить</Button>
      </div>
    )
  } else if (!methods.data) {
    body = <span className="ui-field__hint">Загружаем способы доставки…</span>
  } else {
    body = methods.data.map((method) => {
      const checked = value.includes(method.id)
      const needsAddress = needsShopAddress(method, shop)
      const blocked = needsAddress && !checked
      return (
        <label
          key={method.id}
          className={blocked ? 'delivery-field__option delivery-field__option--disabled' : 'delivery-field__option'}
        >
          <input
            type="checkbox"
            checked={checked}
            disabled={blocked}
            onChange={(event) => toggle(method.id, event.target.checked)}
          />
          <span className="delivery-field__text">
            <span className="delivery-field__name">{method.name}</span>
            <span className={needsAddress && checked ? 'delivery-field__terms delivery-field__terms--error' : 'delivery-field__terms'}>
              {needsAddress ? (
                <>
                  {checked ? 'У магазина не указан адрес — снимите отметку или укажите его в ' : 'Сначала укажите адрес в '}
                  <Link to={`/seller/shops/${shop.id}/profile`}>профиле магазина</Link>
                </>
              ) : method.provider === 'market' ? (
                // Цена и срок — условия для покупателя, продавцу важно, кто везёт
                'Доставляет маркет — вы только передаёте заказ курьеру'
              ) : method.kind === 'pickup' ? (
                `Покупатель забирает: ${shop.address}`
              ) : (
                method.description
              )}
            </span>
          </span>
        </label>
      )
    })
  }

  return (
    <fieldset className="delivery-field" aria-invalid={Boolean(errors?.length)}>
      <legend className="ui-field__label">Способы получения</legend>
      {body}
      {errors?.length ? <FieldError messages={errors} /> : <span className="ui-field__hint">Хотя бы один.</span>}
    </fieldset>
  )
}
