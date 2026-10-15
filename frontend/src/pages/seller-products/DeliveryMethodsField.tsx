import { Link } from 'react-router'
import { formatDeliveryTerms } from '@/entities/delivery'
import { deliveryApi, getErrorMessage, type Shop } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { Button, FieldError } from '@/shared/ui'

const loadMethods = (signal: AbortSignal) => deliveryApi.methods({ signal })

interface DeliveryMethodsFieldProps {
  shop: Shop
  value: number[]
  onChange: (ids: number[]) => void
  errors?: string[]
}

/**
 * Способы получения товара — чекбоксы из справочника маркета.
 * Самовывоз можно выбрать, только если у магазина указан адрес.
 */
export function DeliveryMethodsField({ shop, value, onChange, errors }: DeliveryMethodsFieldProps) {
  const methods = useRequest(loadMethods)

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
      const needsAddress = method.kind === 'pickup' && !shop.address
      return (
        <label
          key={method.id}
          className={needsAddress ? 'delivery-field__option delivery-field__option--disabled' : 'delivery-field__option'}
        >
          <input
            type="checkbox"
            checked={value.includes(method.id)}
            disabled={needsAddress}
            onChange={(event) => toggle(method.id, event.target.checked)}
          />
          <span className="delivery-field__text">
            <span className="delivery-field__name">{method.name}</span>
            <span className="delivery-field__terms">
              {needsAddress ? (
                <>
                  Сначала укажите адрес в{' '}
                  <Link to={`/seller/shops/${shop.id}/profile`}>профиле магазина</Link>
                </>
              ) : method.kind === 'pickup' ? (
                `${formatDeliveryTerms(method)} · ${shop.address}`
              ) : (
                formatDeliveryTerms(method)
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
