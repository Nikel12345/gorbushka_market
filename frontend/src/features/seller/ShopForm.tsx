import { useState, type ChangeEvent, type FormEvent } from 'react'
import { getFieldErrors, type FieldErrors, type ShopPayload } from '@/shared/api'
import { Button, Field, FieldError } from '@/shared/ui'
import './ShopForm.css'

interface ShopFormProps {
  initial?: ShopPayload
  submitLabel: string
  submittingLabel: string
  /** Бросает ошибку API — форма разложит её по полям */
  onSubmit: (payload: ShopPayload) => Promise<void>
  /** Показать после успешного сохранения (форма остаётся на месте) */
  successMessage?: string
}

const EMPTY: Required<ShopPayload> = { name: '', address: '', description: '' }

/** Название, адрес и описание магазина: создание и профиль магазина. */
export function ShopForm({ initial, submitLabel, submittingLabel, onSubmit, successMessage }: ShopFormProps) {
  const [form, setForm] = useState({ ...EMPTY, ...initial })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState(false)

  const update = (field: keyof ShopPayload) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
    setSaved(false)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})
    setSaved(false)
    try {
      await onSubmit({ name: form.name.trim(), address: form.address.trim(), description: form.description.trim() })
      setSaved(true)
    } catch (error) {
      setErrors(getFieldErrors(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="ui-form" onSubmit={handleSubmit} noValidate>
      <FieldError messages={errors.non_field_errors} />
      <Field label="Название" errors={errors.name}>
        <input
          className="ui-input"
          value={form.name}
          onChange={update('name')}
          aria-invalid={Boolean(errors.name)}
          maxLength={255}
          required
        />
      </Field>
      <Field
        label="Адрес"
        errors={errors.address}
        hint="Павильон, ряд, место — где покупатель заберёт товар. Без адреса самовывоз недоступен."
      >
        <input
          className="ui-input"
          value={form.address}
          onChange={update('address')}
          aria-invalid={Boolean(errors.address)}
          maxLength={255}
          placeholder="Например: павильон 2, ряд Б, место 14"
        />
      </Field>
      <Field label="Описание" errors={errors.description} hint="Необязательно. Покупатели увидят его на странице магазина.">
        <textarea
          className="ui-input"
          value={form.description}
          onChange={update('description')}
          aria-invalid={Boolean(errors.description)}
        />
      </Field>
      <div className="shop-form__actions">
        <Button type="submit" variant="primary" disabled={submitting}>
          {submitting ? submittingLabel : submitLabel}
        </Button>
        {saved && successMessage && (
          <span className="shop-form__saved" role="status">
            {successMessage}
          </span>
        )}
      </div>
    </form>
  )
}
