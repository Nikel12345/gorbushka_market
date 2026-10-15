import { useCallback } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { ProductImage } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { ApiError, catalogApi, getErrorMessage } from '@/shared/api'
import { formatDate, formatPrice, useRequest } from '@/shared/lib'
import { Chip, EmptyState, ErrorState, LinkButton, Loader } from '@/shared/ui'
import './ProductPage.css'

/** Страница товара для покупателя: /products/:productId */
export function ProductPage() {
  const productId = Number(useParams().productId)
  const navigate = useNavigate()
  const location = useLocation()

  const load = useCallback((signal: AbortSignal) => catalogApi.getProduct(productId, { signal }), [productId])
  const product = useRequest(load)

  // Пришли из ленты — возвращаемся в неё на то же место; открыли по ссылке — на главную
  const cameFromApp = location.key !== 'default'
  const back = cameFromApp ? (
    <button type="button" className="product-page__back" onClick={() => navigate(-1)}>
      ← Назад
    </button>
  ) : (
    <Link to="/" className="product-page__back">
      ← Все товары
    </Link>
  )

  if (product.status === 'error') {
    const notFound = product.error instanceof ApiError && product.error.status === 404
    return (
      <>
        {back}
        {notFound ? (
          <EmptyState
            title="Товар не найден"
            text="Возможно, продавец снял его с продажи."
            action={<LinkButton to="/">На главную</LinkButton>}
          />
        ) : (
          <ErrorState message={getErrorMessage(product.error)} onRetry={product.reload} />
        )}
      </>
    )
  }

  // При смене товара (другой id) старые данные не показываем
  if (!product.data || product.data.id !== productId) {
    return (
      <>
        {back}
        <Loader />
      </>
    )
  }

  const p = product.data

  return (
    <>
      {back}
      <article className="product-page">
        <div className="product-page__gallery">
          <ProductImage src={p.image} alt={p.title} className="product-page__image" />
        </div>

        <div className="product-page__info">
          <h1 className="product-page__title">{p.title}</h1>
          <p className="product-page__seller">
            Продавец: <span className="product-page__seller-name">{p.shop.name}</span>
          </p>

          <section className="product-page__section">
            <h2 className="product-page__section-title">Описание</h2>
            {p.description ? (
              <p className="product-page__description">{p.description}</p>
            ) : (
              <p className="product-page__description ui-muted">Продавец не добавил описание.</p>
            )}
          </section>

          <section className="product-page__section">
            <h2 className="product-page__section-title">О товаре</h2>
            <dl className="ui-props">
              <dt>Артикул</dt>
              <dd>{p.id}</dd>
              <dt>На витрине с</dt>
              <dd>{formatDate(p.created_at)}</dd>
            </dl>
          </section>
        </div>

        <aside className="product-page__buy" aria-label="Цена и наличие">
          <p className="product-page__price">{formatPrice(p.price)}</p>
          {p.in_stock ? (
            <Chip tone="success">В наличии: {p.quantity} шт.</Chip>
          ) : (
            <Chip tone="warning">Нет в наличии</Chip>
          )}
          <CartControl productId={p.id} canBuy={p.in_stock} max={p.quantity} />
          <p className="product-page__buy-seller">
            Продаёт <span className="product-page__seller-name">{p.shop.name}</span>
          </p>
        </aside>
      </article>
    </>
  )
}
