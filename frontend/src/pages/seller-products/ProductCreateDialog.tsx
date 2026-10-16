import { useState, type FormEvent } from 'react'
import { useCurrentShop } from '@/features/seller'
import { getFieldErrors, sellerApi, type FieldErrors } from '@/shared/api'
import { Button, Dialog, FieldError } from '@/shared/ui'
import { ProductFormFields } from './ProductFormFields'
import { ProductPhotosField } from './ProductPhotosField'
import { EMPTY_PRODUCT_FORM, toProductPayload, useDeliveryMethods, validateProductForm } from './productForm'
import { useProductsOutlet } from './outletContext'
import { newPhotoFiles, type PhotoItem } from './productPhotos'

const FORM_ID = 'product-create-form'

/** Добавление товара: /seller/shops/:shopId/products/new */
export function ProductCreateDialog() {
  const shop = useCurrentShop()
  const { closeDialog, onProductCreated } = useProductsOutlet()
  const methods = useDeliveryMethods()

  const [values, setValues] = useState(EMPTY_PRODUCT_FORM)
  const [photos, setPhotos] = useState<PhotoItem[]>([])
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const localErrors = validateProductForm(values, shop, methods)
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setSubmitting(true)
    try {
      await sellerApi.createProduct(shop.id, { ...toProductPayload(values), images: newPhotoFiles(photos) })
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

        <ProductPhotosField value={photos} onChange={setPhotos} errors={errors.images} />

        <ProductFormFields
          shop={shop}
          methods={methods}
          values={values}
          onChange={setValues}
          errors={errors}
          autoFocus
        />
      </form>
    </Dialog>
  )
}
