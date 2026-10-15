import { useState, type ChangeEvent, type FormEvent } from 'react'
import { ProductImage } from '@/entities/product'
import { useCurrentShop } from '@/features/seller'
import { getFieldErrors, sellerApi, type FieldErrors, type ProductCreatePayload } from '@/shared/api'
import { useObjectUrl } from '@/shared/lib'
import { Button, Dialog, Field, FieldError, FileButton } from '@/shared/ui'
import { useProductsOutlet } from './outletContext'

const FORM_ID = 'product-create-form'
const initialForm = { title: '', price: '', quantity: '1', description: '' }

/** "1 299,90" → "1299.90": бэкенд ждёт десятичное число через точку */
function normalizeDecimal(value: string): string {
  return value.replace(/\s/g, '').replace(',', '.')
}

/** Добавление товара: /seller/shops/:shopId/products/new */
export function ProductCreateDialog() {
  const shop = useCurrentShop()
  const { closeDialog, onProductCreated } = useProductsOutlet()

  const [form, setForm] = useState(initialForm)
  const [image, setImage] = useState<File | null>(null)
  const previewUrl = useObjectUrl(image)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  const update =
    (field: keyof typeof initialForm) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }))

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})

    const payload: ProductCreatePayload = {
      title: form.title.trim(),
      price: normalizeDecimal(form.price),
      description: form.description.trim(),
      image,
    }
    if (form.quantity.trim() !== '') {
      payload.quantity = Number(form.quantity)
    }

    try {
      await sellerApi.createProduct(shop.id, payload)
      onProductCreated()
    } catch (error) {
      setErrors(getFieldErrors(error))
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      title="Новый товар"
      onClose={closeDialog}
      actions={
        <>
          <Button variant="text" onClick={closeDialog}>
            Отмена
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={submitting}>
            {submitting ? 'Сохраняем…' : 'Выставить на продажу'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="ui-form" onSubmit={handleSubmit} noValidate>
        <FieldError messages={errors.non_field_errors} />

        <div className="product-form__photo">
          <ProductImage src={previewUrl} alt="Превью фото" className="product-form__preview" />
          <div className="product-form__photo-side">
            <span className="ui-field__label">Фото</span>
            <div className="product-form__photo-buttons">
              <FileButton accept="image/*" onSelect={setImage}>
                {image ? 'Выбрать другое' : 'Выбрать фото'}
              </FileButton>
              {image && (
                <Button variant="text" onClick={() => setImage(null)}>
                  Убрать
                </Button>
              )}
            </div>
            {image ? (
              <span className="product-form__file-name" title={image.name}>
                {image.name}
              </span>
            ) : (
              <span className="ui-field__hint">JPG, PNG или WebP. Можно добавить позже.</span>
            )}
            <FieldError messages={errors.image} />
          </div>
        </div>

        <Field label="Название" errors={errors.title}>
          <input
            className="ui-input"
            value={form.title}
            onChange={update('title')}
            aria-invalid={Boolean(errors.title)}
            maxLength={255}
            required
            data-autofocus
          />
        </Field>

        <div className="ui-form__row">
          <Field label="Цена, ₽" errors={errors.price}>
            <input
              className="ui-input"
              inputMode="decimal"
              placeholder="0,00"
              value={form.price}
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
              value={form.quantity}
              onChange={update('quantity')}
              aria-invalid={Boolean(errors.quantity)}
            />
          </Field>
        </div>

        <Field label="Описание" errors={errors.description}>
          <textarea
            className="ui-input"
            value={form.description}
            onChange={update('description')}
            aria-invalid={Boolean(errors.description)}
          />
        </Field>
      </form>
    </Dialog>
  )
}
