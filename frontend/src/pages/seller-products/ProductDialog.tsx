import { useCallback, useState, type FormEvent } from 'react'
import { useParams } from 'react-router'
import { ProductImage } from '@/entities/product'
import { useCurrentShop } from '@/features/seller'
import { ApiError, getErrorMessage, getFieldErrors, sellerApi, type FieldErrors, type Product } from '@/shared/api'
import { formatDateTime, formatPrice, useRequest } from '@/shared/lib'
import { Button, Chip, Dialog, ErrorState, FieldError, Loader } from '@/shared/ui'
import { ProductFormFields } from './ProductFormFields'
import { ProductPhotosField } from './ProductPhotosField'
import {
  productToFormValues,
  toProductPayload,
  useDeliveryMethods,
  validateProductForm,
  type ProductFormValues,
} from './productForm'
import { useProductsOutlet } from './outletContext'
import { photosFromProduct, saveProductWithPhotos, type PhotoItem } from './productPhotos'

const EDIT_FORM_ID = 'product-edit-form'

/**
 * Карточка товара: /seller/shops/:shopId/products/:productId
 * Просмотр → «Редактировать» открывает ту же форму, что при добавлении (вместе с фото).
 */
export function ProductDialog() {
  const shop = useCurrentShop()
  const productId = Number(useParams().productId)
  const { closeDialog, onProductArchived, onProductUpdated } = useProductsOutlet()

  const load = useCallback(
    (signal: AbortSignal) => sellerApi.getProduct(shop.id, productId, { signal }),
    [shop.id, productId],
  )
  const product = useRequest(load)
  const { mutate } = product

  // --- Редактирование ---

  const methods = useDeliveryMethods()
  /** null — режим просмотра */
  const [editValues, setEditValues] = useState<ProductFormValues | null>(null)
  const [editPhotos, setEditPhotos] = useState<PhotoItem[]>([])
  const [editErrors, setEditErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)

  function startEditing(p: Product) {
    setEditValues(productToFormValues(p))
    setEditPhotos(photosFromProduct(p))
    setEditErrors({})
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    if (!editValues || !product.data) return
    const localErrors = validateProductForm(editValues, shop, methods)
    setEditErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setSaving(true)
    try {
      const updated = await saveProductWithPhotos(shop.id, product.data, toProductPayload(editValues), editPhotos)
      mutate(() => updated)
      onProductUpdated()
      setEditValues(null)
    } catch (error) {
      setEditErrors(getFieldErrors(error))
      // Часть шагов (удаление фото) могла пройти — перечитываем товар, форму не трогаем
      product.reload()
      onProductUpdated()
    } finally {
      setSaving(false)
    }
  }

  // --- Снятие с продажи ---

  const [confirming, setConfirming] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [archiveError, setArchiveError] = useState<string[]>()

  async function handleArchive() {
    setArchiving(true)
    setArchiveError(undefined)
    try {
      await sellerApi.archiveProduct(shop.id, productId)
      onProductArchived()
    } catch (error) {
      setArchiveError([getErrorMessage(error)])
      setArchiving(false)
    }
  }

  // У кнопок в панели действий — ключи. Без них React переиспользует DOM-кнопку:
  // «Редактировать» стала бы «Сохранить» (type=submit) ещё до того, как браузер закончил
  // обрабатывать клик, и тот же клик сразу отправил бы форму.
  let body
  let actions
  if (product.data && product.status !== 'error') {
    const p = product.data

    if (editValues) {
      body = (
        <form id={EDIT_FORM_ID} className="ui-form" onSubmit={handleSave} noValidate>
          <FieldError messages={editErrors.non_field_errors} />
          <ProductPhotosField value={editPhotos} onChange={setEditPhotos} errors={editErrors.images} />
          <ProductFormFields
            shop={shop}
            methods={methods}
            values={editValues}
            onChange={setEditValues}
            errors={editErrors}
            autoFocus
          />
        </form>
      )
      actions = (
        <>
          <Button key="cancel-edit" variant="text" onClick={() => setEditValues(null)} disabled={saving}>
            Отмена
          </Button>
          <Button key="save" type="submit" form={EDIT_FORM_ID} variant="primary" disabled={saving}>
            {saving ? 'Сохраняем…' : 'Сохранить'}
          </Button>
        </>
      )
    } else {
      body = (
        <div className="product-card">
          <ProductGallery product={p} />
          <ProductDetails product={p} />
        </div>
      )
      actions = confirming ? (
        <>
          <p key="confirm-text" className="product-card__confirm">
            Товар пропадёт из продажи. Заказы с ним останутся в истории.
          </p>
          <FieldError key="confirm-error" messages={archiveError} />
          <Button key="cancel-archive" variant="text" onClick={() => setConfirming(false)} disabled={archiving}>
            Отмена
          </Button>
          <Button key="archive" variant="danger" onClick={handleArchive} disabled={archiving}>
            {archiving ? 'Снимаем…' : 'Снять с продажи'}
          </Button>
        </>
      ) : (
        <>
          <Button key="ask-archive" onClick={() => setConfirming(true)}>
            Снять с продажи
          </Button>
          <span key="spacer" className="ui-spacer" />
          <Button key="edit" onClick={() => startEditing(p)}>
            Редактировать
          </Button>
          <Button key="close" variant="primary" onClick={closeDialog}>
            Закрыть
          </Button>
        </>
      )
    }
  } else if (product.status === 'error') {
    const notFound = product.error instanceof ApiError && product.error.status === 404
    body = (
      <ErrorState
        message={notFound ? 'Товар не найден или уже снят с продажи.' : getErrorMessage(product.error)}
        onRetry={notFound ? undefined : product.reload}
      />
    )
  } else {
    body = <Loader />
  }

  let title = 'Товар'
  if (editValues) title = 'Редактирование товара'
  else if (product.data) title = product.data.title

  return (
    <Dialog title={title} size="wide" onClose={closeDialog} actions={actions}>
      {body}
    </Dialog>
  )
}

function ProductDetails({ product: p }: { product: Product }) {
  return (
    <div>
      <p className="product-card__price">{formatPrice(p.price)}</p>
      <dl className="ui-props">
        <dt>В наличии</dt>
        <dd>{p.quantity > 0 ? `${p.quantity} шт.` : <Chip tone="warning">Нет в наличии</Chip>}</dd>
        <dt>Получение</dt>
        <dd>
          {p.delivery_methods.length > 0 ? (
            p.delivery_methods.map((method) => method.name).join(', ')
          ) : (
            <span className="ui-muted">не указано</span>
          )}
        </dd>
        <dt>Статус</dt>
        <dd>
          <Chip tone="success">{p.status_display}</Chip>
        </dd>
        <dt>Номер</dt>
        <dd>{p.id}</dd>
        <dt>Добавлен</dt>
        <dd>{formatDateTime(p.created_at)}</dd>
        <dt>Изменён</dt>
        <dd>{formatDateTime(p.updated_at)}</dd>
      </dl>

      <h3 className="product-card__section-title">Описание</h3>
      <p className="product-card__description">
        {p.description || <span className="ui-muted">Описание не заполнено</span>}
      </p>
    </div>
  )
}

/** Просмотр: большое фото и миниатюры остальных */
function ProductGallery({ product: p }: { product: Product }) {
  const [current, setCurrent] = useState(0)
  const shown = p.images[current] ?? p.images[0]

  return (
    <div className="product-card__gallery">
      <ProductImage src={shown?.url ?? p.image} alt={p.title} className="product-card__image" />
      {p.images.length > 1 && (
        <div className="product-card__thumbs">
          {p.images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              className="product-card__thumb"
              aria-pressed={image.id === shown?.id}
              aria-label={`Фото ${index + 1}`}
              onClick={() => setCurrent(index)}
            >
              <ProductImage src={image.url} alt="" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
