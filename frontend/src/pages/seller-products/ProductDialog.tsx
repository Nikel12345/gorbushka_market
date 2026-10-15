import { useCallback, useState } from 'react'
import { useParams } from 'react-router'
import { ProductImage } from '@/entities/product'
import { useCurrentShop } from '@/features/seller'
import { ApiError, getErrorMessage, getFieldErrors, sellerApi } from '@/shared/api'
import { formatDateTime, formatPrice, useRequest } from '@/shared/lib'
import { Button, Chip, Dialog, ErrorState, FieldError, FileButton, Loader } from '@/shared/ui'
import { useProductsOutlet } from './outletContext'

/** Карточка товара: /seller/shops/:shopId/products/:productId */
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

  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoError, setPhotoError] = useState<string[]>()

  /** Новый файл — заменить фото, null — удалить. Сохраняется сразу. */
  async function changePhoto(file: File | null) {
    setPhotoBusy(true)
    setPhotoError(undefined)
    try {
      const updated = await sellerApi.updateProductImage(shop.id, productId, file)
      mutate(() => updated)
      onProductUpdated()
    } catch (error) {
      const errors = getFieldErrors(error)
      setPhotoError(errors.image ?? errors.non_field_errors ?? Object.values(errors).flat())
    } finally {
      setPhotoBusy(false)
    }
  }

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

  let body
  let actions
  if (product.status === 'success') {
    const p = product.data
    body = (
      <div className="product-card">
        <div className="product-card__media">
          <ProductImage src={p.image} alt={p.title} className="product-card__image">
            {photoBusy && <span className="product-card__uploading">Сохраняем…</span>}
          </ProductImage>
          <div className="product-card__photo-actions">
            <FileButton accept="image/*" onSelect={changePhoto} disabled={photoBusy}>
              {p.image ? 'Заменить фото' : 'Загрузить фото'}
            </FileButton>
            {p.image && (
              <Button variant="text" onClick={() => changePhoto(null)} disabled={photoBusy}>
                Удалить
              </Button>
            )}
          </div>
          <FieldError messages={photoError} />
        </div>
        <div>
          <p className="product-card__price">{formatPrice(p.price)}</p>
          <dl className="ui-props">
            <dt>В наличии</dt>
            <dd>{p.quantity > 0 ? `${p.quantity} шт.` : <Chip tone="warning">Нет в наличии</Chip>}</dd>
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
      </div>
    )

    actions = confirming ? (
      <>
        <p className="product-card__confirm">
          Товар пропадёт из продажи. Заказы с ним останутся в истории.
        </p>
        <FieldError messages={archiveError} />
        <Button variant="text" onClick={() => setConfirming(false)} disabled={archiving}>
          Отмена
        </Button>
        <Button variant="danger" onClick={handleArchive} disabled={archiving}>
          {archiving ? 'Снимаем…' : 'Снять с продажи'}
        </Button>
      </>
    ) : (
      <>
        <Button onClick={() => setConfirming(true)}>Снять с продажи</Button>
        <span className="ui-spacer" />
        <Button variant="primary" onClick={closeDialog}>
          Закрыть
        </Button>
      </>
    )
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

  const title = product.status === 'success' ? product.data.title : 'Товар'

  return (
    <Dialog title={title} size="wide" onClose={closeDialog} actions={actions}>
      {body}
    </Dialog>
  )
}
