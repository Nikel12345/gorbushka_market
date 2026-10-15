import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { useSeller } from '@/features/seller'
import { getFieldErrors, sellerApi, type FieldErrors } from '@/shared/api'
import { Button, Card, Field, FieldError, PageHeader } from '@/shared/ui'

/** /seller — ведёт в текущий магазин, а если магазинов нет — предлагает создать. */
export function SellerHomePage() {
  const { activeShopId } = useSeller()

  if (activeShopId !== null) {
    return <Navigate to={`/seller/shops/${activeShopId}/products`} replace />
  }

  return <CreateFirstShop />
}

function CreateFirstShop() {
  const { addShop } = useSeller()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})
    try {
      const shop = await sellerApi.createShop({ name: name.trim(), description: description.trim() })
      addShop({ id: shop.id, name: shop.name })
      navigate(`/seller/shops/${shop.id}/products`, { replace: true })
    } catch (error) {
      setErrors(getFieldErrors(error))
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="Добро пожаловать" subtitle="Чтобы начать продавать, создайте магазин." />
      <Card title="Новый магазин">
        <form className="ui-form" onSubmit={handleSubmit} noValidate>
          <FieldError messages={errors.non_field_errors} />
          <Field label="Название" errors={errors.name}>
            <input
              className="ui-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={Boolean(errors.name)}
              maxLength={255}
              required
            />
          </Field>
          <Field label="Описание" errors={errors.description} hint="Необязательно. Покупатели увидят его на странице магазина.">
            <textarea
              className="ui-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              aria-invalid={Boolean(errors.description)}
            />
          </Field>
          <div>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? 'Создаём…' : 'Создать магазин'}
            </Button>
          </div>
        </form>
      </Card>
    </>
  )
}
