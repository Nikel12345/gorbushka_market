import { useCallback, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { formatDeliveryTerms } from '@/entities/delivery'
import { ProductImage } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { ApiError, catalogApi, getErrorMessage, type ProductDetail } from '@/shared/api'
import { formatPrice, pluralize, useRequest } from '@/shared/lib'
import { EmptyState, ErrorState, LinkButton, Loader } from '@/shared/ui'
import './ProductPage.css'

// TODO: заглушки, пока нет отзывов на бэкенде
const RATING_STUB = { rating: 4.8, reviews: 23 }

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
      <header className="product-page__head">
        <h1 className="product-page__title">{p.title}</h1>
        <span className="product-page__sku">Артикул {p.id}</span>
      </header>

      <article className="product-page">
        <Gallery product={p} />

        <div className="product-page__info">
          <div className="product-page__summary">
            <Summary description={p.description} />
            <p className="product-page__seller">
              <span className="ui-muted">Продавец</span>
              <Link to={`/shops/${p.shop.id}`} className="product-page__seller-name">
                {p.shop.name}
              </Link>
            </p>
          </div>

          <div className="product-page__badges">
            <span className="product-page__badge">
              <StarIcon />
              <b>{RATING_STUB.rating.toLocaleString('ru-RU')}</b>
              <span className="product-page__badge-sep" />
              {pluralize(RATING_STUB.reviews, ['отзыв', 'отзыва', 'отзывов'])}
            </span>
          </div>

          <div className="product-page__buy">
            <div className="product-page__price-box">
              <span className="product-page__price">{formatPrice(p.price)}</span>
            </div>
            <FavoriteButton />
            <div className="product-page__cart">
              <CartControl productId={p.id} canBuy={p.in_stock} max={p.quantity} />
            </div>
          </div>

          <ul className="product-page__tiles">
            <li className="product-page__tile">
              <span>{p.in_stock ? 'В наличии' : 'Нет в наличии'}</span>
              {p.in_stock && <span className="product-page__tile-accent">{p.quantity} шт.</span>}
            </li>
            {p.delivery_methods.map((method) => (
              <li key={method.id} className="product-page__tile">
                <span>{method.name}</span>
                <span className="product-page__tile-accent">{formatDeliveryTerms(method)}</span>
              </li>
            ))}
          </ul>

          {/* Место под варианты товара (цвет, память и т. п.) — появятся вместе с характеристиками */}
          <section className="product-page__variants" aria-label="Варианты товара">
            <span className="product-page__variants-title">Варианты</span>
            <div className="product-page__variants-stub">Другие варианты этого товара появятся здесь</div>
          </section>
        </div>
      </article>
    </>
  )
}

/** Колонка миниатюр + большое фото. Пока у товара одно фото — миниатюра одна. */
function Gallery({ product: p }: { product: ProductDetail }) {
  const [current, setCurrent] = useState(0)
  const shown = p.images[current] ?? p.images[0]

  return (
    <div className="product-page__gallery">
      {p.images.length > 1 && (
        <div className="product-page__thumbs">
          {p.images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              className={
                image.id === shown?.id ? 'product-page__thumb product-page__thumb--active' : 'product-page__thumb'
              }
              aria-label={`Фото ${index + 1}`}
              aria-pressed={image.id === shown?.id}
              onClick={() => setCurrent(index)}
              onMouseEnter={() => setCurrent(index)}
            >
              <ProductImage src={image.url} alt="" />
            </button>
          ))}
        </div>
      )}
      <ProductImage src={shown?.url ?? p.image} alt={p.title} className="product-page__image" />
    </div>
  )
}

/**
 * Кратко о товаре. Здесь будут основные характеристики категории; пока их нет —
 * начало описания. «Подробнее» поведёт к полному описанию и характеристикам.
 */
function Summary({ description }: { description: string }) {
  if (!description) return <p className="product-page__description ui-muted">Продавец не добавил описание.</p>
  return (
    <div>
      <p className="product-page__description">{description}</p>
      <button type="button" className="product-page__more">
        Подробнее ›
      </button>
    </div>
  )
}

// TODO: заглушка — избранное пока только в этой вкладке, на сервер не сохраняется
function FavoriteButton() {
  const [active, setActive] = useState(false)
  return (
    <button
      type="button"
      className={`product-page__favorite${active ? ' product-page__favorite--active' : ''}`}
      onClick={() => setActive((value) => !value)}
      aria-pressed={active}
      aria-label={active ? 'Убрать из избранного' : 'Добавить в избранное'}
      title={active ? 'Убрать из избранного' : 'В избранное'}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20.5l-1.3-1.2C5.6 14.7 2.5 11.9 2.5 8.4 2.5 5.6 4.7 3.5 7.4 3.5c1.6 0 3.1.7 4.1 1.9 1-1.2 2.5-1.9 4.1-1.9 2.7 0 4.9 2.1 4.9 4.9 0 3.5-3.1 6.3-8.2 10.9L12 20.5z" />
      </svg>
    </button>
  )
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="product-page__star">
      <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" />
    </svg>
  )
}
