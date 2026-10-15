import { useCallback, useState } from 'react'
import { useParams } from 'react-router'
import { useCurrentShop } from '@/features/seller'
import { ApiError, getErrorMessage, sellerApi } from '@/shared/api'
import { formatDateTime, formatPrice, useRequest } from '@/shared/lib'
import { Button, Chip, Dialog, ErrorState, FieldError, Loader } from '@/shared/ui'
import { useProductsOutlet } from './outletContext'

/** Карточка товара: /seller/shops/:shopId/products/:productId */
export function ProductDialog() {
  const shop = useCurrentShop()
  const productId = Number(useParams().productId)
  const { closeDialog, onProductArchived } = useProductsOutlet()

  const load = useCallback(
    (signal: AbortSignal) => sellerApi.getProduct(shop.id, productId, { signal }),
    [shop.id, productId],
  )
  const product = useRequest(load)

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
      <>
        <dl className="ui-props">
          <dt>Цена</dt>
          <dd>{formatPrice(p.price)}</dd>
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
      </>
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
        <Button variant="text" onClick={() => setConfirming(true)}>
          Снять с продажи
        </Button>
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
    <Dialog title={title} onClose={closeDialog} actions={actions}>
      {body}
    </Dialog>
  )
}
