import type { ChangeEvent } from 'react'
import type { FieldErrors, Shop } from '@/shared/api'
import { Field } from '@/shared/ui'
import { DeliveryMethodsField } from './DeliveryMethodsField'
import type { DeliveryMethodsRequest, ProductFormValues } from './productForm'

interface ProductFormFieldsProps {
  shop: Shop
  methods: DeliveryMethodsRequest
  values: ProductFormValues
  onChange: (values: ProductFormValues) => void
  errors: FieldErrors
  /** Поле названия получает фокус при открытии диалога */
  autoFocus?: boolean
}

/** Название, цена, количество, способы получения, описание — общие для добавления и правки товара. */
export function ProductFormFields({ shop, methods, values, onChange, errors, autoFocus }: ProductFormFieldsProps) {
  const update =
    (field: Exclude<keyof ProductFormValues, 'deliveryIds'>) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...values, [field]: event.target.value })

  return (
    <>
      <Field label="Название" errors={errors.title}>
        <input
          className="ui-input"
          value={values.title}
          onChange={update('title')}
          aria-invalid={Boolean(errors.title)}
          maxLength={255}
          required
          // data-autofocus — для открытия диалога, autoFocus — когда поля появляются позже (режим правки)
          data-autofocus={autoFocus || undefined}
          autoFocus={autoFocus}
        />
      </Field>

      <div className="ui-form__row">
        <Field label="Цена, ₽" errors={errors.price}>
          <input
            className="ui-input"
            inputMode="decimal"
            placeholder="0,00"
            value={values.price}
            onChange={update('price')}
            aria-invalid={Boolean(errors.price)}
            required
          />
        </Field>
        <Field label="В наличии, шт." errors={errors.quantity}>
          <input
            className="ui-input"
            type="number"
            min={0}
            step={1}
            value={values.quantity}
            onChange={update('quantity')}
            aria-invalid={Boolean(errors.quantity)}
          />
        </Field>
      </div>

      <DeliveryMethodsField
        shop={shop}
        methods={methods}
        value={values.deliveryIds}
        onChange={(deliveryIds) => onChange({ ...values, deliveryIds })}
        errors={errors.delivery_method_ids}
      />

      <Field label="Описание" errors={errors.description}>
        <textarea
          className="ui-input"
          value={values.description}
          onChange={update('description')}
          aria-invalid={Boolean(errors.description)}
        />
      </Field>
    </>
  )
}
