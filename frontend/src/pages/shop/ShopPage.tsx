import { useCallback, useState } from 'react'
import { useParams } from 'react-router'
import { ProductCatalog } from '@/features/product-catalog'
import { ApiError, getErrorMessage, shopsApi, type ShopPublic } from '@/shared/api'
import { pluralize, useRequest } from '@/shared/lib'
import { Avatar, EmptyState, ErrorState, LinkButton, Loader } from '@/shared/ui'
import './ShopPage.css'

// TODO: заглушки, пока нет отзывов о магазинах на бэкенде
const RATING_STUB = { rating: 4.9, reviews: 56 }

// Месяц с числом Intl отдаёт в родительном падеже («октября») — берём его оттуда
const monthFormatter = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })

/** «октября 2026» — для «На маркете с …» */
function formatSince(iso: string): string {
  const date = new Date(iso)
  const month = monthFormatter.formatToParts(date).find((part) => part.type === 'month')?.value
  return `${month} ${date.getFullYear()}`
}

/** Страница магазина: /shops/:shopId — карточка магазина и его каталог (фильтры, сортировка, лента). */
export function ShopPage() {
  const shopId = Number(useParams().shopId)
  const load = useCallback((signal: AbortSignal) => shopsApi.get(shopId, { signal }), [shopId])
  const shop = useRequest(load)

  if (shop.status === 'error') {
    const notFound = shop.error instanceof ApiError && shop.error.status === 404
    return notFound ? (
      <EmptyState
        title="Магазин не найден"
        text="Возможно, он закрылся или временно скрыт."
        action={<LinkButton to="/">На главную</LinkButton>}
      />
    ) : (
      <ErrorState message={getErrorMessage(shop.error)} onRetry={shop.reload} />
    )
  }

  if (!shop.data || shop.data.id !== shopId) return <Loader />

  return (
    <>
      <ShopHero shop={shop.data} />
      {/* key — при переходе в другой магазин лента начинается заново */}
      <ProductCatalog
        key={shopId}
        shopId={shopId}
        heading="h2"
        title="Товары магазина"
        emptyText="У магазина пока нет товаров на продаже."
      />
    </>
  )
}

function ShopHero({ shop }: { shop: ShopPublic }) {
  const [expanded, setExpanded] = useState(false)
  const longDescription = shop.description.length > 240

  return (
    <section className="shop-hero">
      <Avatar name={shop.name} size={72} />

      <div className="shop-hero__main">
        <h1 className="shop-hero__name">{shop.name}</h1>
        <ul className="shop-hero__facts">
          <li className="shop-hero__rating">
            <StarIcon />
            <b>{RATING_STUB.rating.toLocaleString('ru-RU')}</b>
            <span className="ui-muted">· {pluralize(RATING_STUB.reviews, ['отзыв', 'отзыва', 'отзывов'])}</span>
          </li>
          <li>{pluralize(shop.products_count, ['товар', 'товара', 'товаров'])} на продаже</li>
          <li className="ui-muted">На маркете с {formatSince(shop.created_at)}</li>
        </ul>
        {shop.address && (
          <p className="shop-hero__address">
            <PinIcon />
            {shop.address}
          </p>
        )}
        {shop.description && (
          <div className="shop-hero__about">
            <p className={expanded ? 'shop-hero__description' : 'shop-hero__description shop-hero__description--clamped'}>
              {shop.description}
            </p>
            {longDescription && (
              <button type="button" className="shop-hero__more" onClick={() => setExpanded((value) => !value)}>
                {expanded ? 'Свернуть' : 'Подробнее'}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="shop-hero__actions">
        <SubscribeButton />
      </div>
    </section>
  )
}

// TODO: заглушка — подписка на магазин пока только в этой вкладке, на сервер не сохраняется
function SubscribeButton() {
  const [subscribed, setSubscribed] = useState(false)
  return (
    <button
      type="button"
      className={subscribed ? 'shop-hero__subscribe shop-hero__subscribe--on' : 'shop-hero__subscribe'}
      aria-pressed={subscribed}
      onClick={() => setSubscribed((value) => !value)}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20.5l-1.3-1.2C5.6 14.7 2.5 11.9 2.5 8.4 2.5 5.6 4.7 3.5 7.4 3.5c1.6 0 3.1.7 4.1 1.9 1-1.2 2.5-1.9 4.1-1.9 2.7 0 4.9 2.1 4.9 4.9 0 3.5-3.1 6.3-8.2 10.9L12 20.5z" />
      </svg>
      {subscribed ? 'Вы подписаны' : 'Подписаться'}
    </button>
  )
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="shop-hero__star">
      <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="shop-hero__pin">
      <path d="M12 2a7 7 0 017 7c0 5-7 13-7 13S5 14 5 9a7 7 0 017-7zm0 4.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z" />
    </svg>
  )
}
