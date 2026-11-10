import { useCallback, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { formatDeliveryPrice } from '@/entities/delivery'
import { ProductImage } from '@/entities/product'
import { CartControl, useCart } from '@/features/cart'
import type { ShowcaseDesignId } from '@/features/design-switcher'
import { ProductReviews, REVIEWS_ANCHOR } from '@/features/product-reviews'
import {
  ApiError,
  catalogApi,
  getErrorMessage,
  type DeliveryMethod,
  type ProductDetail,
  type ProductVariantRow,
} from '@/shared/api'
import { store } from '@/shared/config'
import { formatPrice, formatRating, pluralize, useRequest } from '@/shared/lib'
import { EmptyState, ErrorState, LinkButton, Loader } from '@/shared/ui'
import { FavoriteToggle } from './FavoriteToggle'
import { ArrowIcon, StarIcon, StoreIcon, TruckIcon } from './icons'
import { ShowcaseTile } from './ShowcaseTile'

interface ProductLocationState {
  cameFromApp?: boolean
}

const DAY_WORDS: [string, string, string] = ['день', 'дня', 'дней']

/** «Игровая консоль Sony PlayStation 5…» → тип «Игровая консоль» и название «Sony PlayStation 5…» */
function splitTitle(title: string): { type: string | null; name: string } {
  const match = title.match(/^([А-ЯЁа-яё][А-ЯЁа-яё\s-]+?)\s+(?=[A-Za-z0-9])/)
  return match ? { type: match[1].trim(), name: title.slice(match[0].length) } : { type: null, name: title }
}

function scrollToReviews() {
  document.getElementById(REVIEWS_ANCHOR)?.scrollIntoView({ behavior: 'smooth' })
}

/** Цены вариантов для подписей под кнопками: у варианта — свой товар со своей ценой */
function useVariantPrices(product: ProductDetail): Map<number, string> {
  const ids = [
    ...new Set(product.variants.flatMap((row) => row.options.filter((option) => !option.selected).map((o) => o.product_id))),
  ]
  const key = ids.join(',')
  const load = useCallback(
    async (signal: AbortSignal) => {
      const results = await Promise.allSettled(
        key ? key.split(',').map((id) => catalogApi.getProduct(Number(id), { signal })) : [],
      )
      return new Map(
        results.flatMap((result) => (result.status === 'fulfilled' ? [[result.value.id, result.value.price] as const] : [])),
      )
    },
    [key],
  )
  const prices = useRequest(load).data ?? new Map<number, string>()
  return new Map([...prices, [product.id, product.price]])
}

function Variants({
  rows,
  prices,
  cameFromApp,
}: {
  rows: ProductVariantRow[]
  prices: Map<number, string>
  cameFromApp: boolean
}) {
  if (rows.length === 0) return null
  return (
    <section className="sc-variants" aria-label="Варианты товара">
      {rows.map((row) => {
        const selected = row.options.find((option) => option.selected)
        return (
          <div key={row.characteristic_id} className="sc-variants__row">
            <h2 className="sc-variants__title">
              {row.name}
              {selected && <b>: {selected.value}</b>}
            </h2>
            <div className="sc-variants__options">
              {row.options.map((option) => {
                const price = prices.get(option.product_id)
                const body = (
                  <>
                    <span className="sc-variant__value">{option.value}</span>
                    {price && <span className="sc-variant__price">{formatPrice(price)}</span>}
                  </>
                )
                return option.selected ? (
                  <span key={option.value_id} className="sc-variant sc-variant--selected" aria-current="true">
                    {body}
                  </span>
                ) : (
                  <Link
                    key={option.value_id}
                    to={`/products/${option.product_id}`}
                    replace
                    preventScrollReset
                    state={{ cameFromApp } satisfies ProductLocationState}
                    className={option.in_stock ? 'sc-variant' : 'sc-variant sc-variant--out'}
                    title={option.in_stock ? undefined : 'Нет в наличии'}
                  >
                    {body}
                  </Link>
                )
              })}
            </div>
          </div>
        )
      })}
    </section>
  )
}

function Gallery({ product: p }: { product: ProductDetail }) {
  const [current, setCurrent] = useState(0)
  const shown = p.images[current] ?? p.images[0]

  return (
    <div className="sc-gallery">
      <div className="sc-gallery__main">
        <ProductImage src={shown?.url ?? p.image} alt={p.title} />
        {!p.in_stock && <span className="sc-gallery__badge">Нет в наличии</span>}
      </div>
      {p.images.length > 1 && (
        <div className="sc-gallery__thumbs">
          {p.images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              className={image.id === shown?.id ? 'sc-gallery__thumb sc-gallery__thumb--active' : 'sc-gallery__thumb'}
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
    </div>
  )
}

function Rating({ product: p }: { product: ProductDetail }) {
  return (
    <button type="button" className="sc-rating-link" onClick={scrollToReviews}>
      <StarIcon empty={p.reviews_count === 0} />
      {p.reviews_count > 0 ? (
        <>
          <b>{formatRating(p.rating)}</b>
          <span>· {pluralize(p.reviews_count, ['отзыв', 'отзыва', 'отзывов'])}</span>
        </>
      ) : (
        'Нет отзывов'
      )}
    </button>
  )
}

/** «Добавить в корзину» и «Купить в 1 клик» (кладёт в корзину и ведёт к оформлению) */
function BuyButtons({ product: p }: { product: ProductDetail }) {
  const cart = useCart()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  async function buyNow() {
    setError(null)
    try {
      if (cart.quantityOf(p.id) === 0) await cart.add(p.id)
      navigate('/checkout')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="sc-buy">
      <div className="sc-buy__cart">
        <CartControl productId={p.id} canBuy={p.in_stock} max={p.quantity} />
      </div>
      {p.in_stock && (
        <button type="button" className="sc-buy__now" onClick={buyNow} disabled={cart.isPending(p.id)}>
          Купить в 1 клик
        </button>
      )}
      {error && (
        <p className="sc-buy__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

function deliveryNote(method: DeliveryMethod): string {
  const parts: string[] = []
  if (method.eta) {
    const { min_days: min, max_days: max } = method.eta
    parts.push(min === max ? pluralize(min, DAY_WORDS) : `${min}–${pluralize(max, DAY_WORDS)}`)
  }
  if (method.kind === 'pickup') parts.push(`${store.address.replace(/^Москва,\s*/, '')} · место покажем при оформлении`)
  else if (method.has_slots) parts.push('интервал выберете при оформлении')
  return parts.join(', ')
}

function StockLine({ product: p }: { product: ProductDetail }) {
  return (
    <p className={p.in_stock ? 'sc-stock' : 'sc-stock sc-stock--out'}>
      <span className="sc-stock__dot" />
      {p.in_stock ? `В наличии · ${p.quantity} шт.` : 'Нет в наличии'}
    </p>
  )
}

function DeliveryList({ methods }: { methods: DeliveryMethod[] }) {
  if (methods.length === 0) return null
  return (
    <ul className="sc-delivery">
      {methods.map((method) => (
        <li key={method.id} className="sc-delivery__item">
          <span className="sc-delivery__icon">{method.kind === 'pickup' ? <StoreIcon /> : <TruckIcon />}</span>
          <span>
            <b>
              {method.name} — {formatDeliveryPrice(method.price)}
            </b>
            <small>{deliveryNote(method)}</small>
          </span>
        </li>
      ))}
    </ul>
  )
}

function Specs({ product: p, limit }: { product: ProductDetail; limit?: number }) {
  const [all, setAll] = useState(false)
  if (p.characteristics.length === 0) return null
  const shown = limit && !all ? p.characteristics.slice(0, limit) : p.characteristics

  return (
    <section className="sc-specs">
      <h2 className="sc-specs__title">Характеристики</h2>
      <dl className="sc-specs__list">
        {shown.map((item) => (
          <div key={item.characteristic_id} className="sc-specs__row">
            <dt>{item.name}</dt>
            <span className="sc-specs__dots" aria-hidden="true" />
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
      {limit && p.characteristics.length > limit && (
        <button type="button" className="sc-more-link" onClick={() => setAll((value) => !value)}>
          {all ? 'Свернуть' : 'Все характеристики'}
          <ArrowIcon />
        </button>
      )}
    </section>
  )
}

function Related({ productId, title }: { productId: number; title: string }) {
  const load = useCallback((signal: AbortSignal) => catalogApi.accessories(productId, { signal }), [productId])
  const products = useRequest(load).data
  if (!products?.length) return null

  return (
    <section className="sc-related">
      <h2 className="sc-related__title">{title}</h2>
      <ul className="sc-grid sc-grid--related">
        {products.map((product) => (
          <li key={product.id}>
            <ShowcaseTile product={product} />
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Страница товара «витринных» вариантов — раскладка по макету каждого варианта */
export function ShowcaseProductPage({ design }: { design: ShowcaseDesignId }) {
  const productId = Number(useParams().productId)
  const navigate = useNavigate()
  const location = useLocation()

  const load = useCallback((signal: AbortSignal) => catalogApi.getProduct(productId, { signal }), [productId])
  const product = useRequest(load)
  const cameFromApp = (location.state as ProductLocationState | null)?.cameFromApp ?? location.key !== 'default'

  const back = cameFromApp ? (
    <button type="button" className="sc-back" onClick={() => navigate(-1)}>
      ← Назад
    </button>
  ) : (
    <Link to="/" className="sc-back">
      ← Все товары
    </Link>
  )

  if (product.status === 'error') {
    const notFound = product.error instanceof ApiError && product.error.status === 404
    return (
      <div className={`sc-product sc-product--${design}`}>
        {back}
        {notFound ? (
          <EmptyState
            title="Товар не найден"
            text="Возможно, его сняли с продажи."
            action={<LinkButton to="/">На главную</LinkButton>}
          />
        ) : (
          <ErrorState message={getErrorMessage(product.error)} onRetry={product.reload} />
        )}
      </div>
    )
  }

  const variantIds = product.data?.variants.flatMap((row) => row.options.map((option) => option.product_id))
  if (!product.data || (product.data.id !== productId && !variantIds?.includes(productId))) {
    return (
      <div className={`sc-product sc-product--${design}`}>
        {back}
        <Loader />
      </div>
    )
  }

  return (
    <ProductLayout
      key={product.data.id}
      design={design}
      product={product.data}
      busy={product.data.id !== productId}
      cameFromApp={cameFromApp}
      onReviewsChanged={product.reload}
    />
  )
}

function ProductLayout({
  design,
  product: p,
  busy,
  cameFromApp,
  onReviewsChanged,
}: {
  design: ShowcaseDesignId
  product: ProductDetail
  busy: boolean
  cameFromApp: boolean
  onReviewsChanged: () => void
}) {
  const prices = useVariantPrices(p)
  const { type, name } = splitTitle(p.title)
  const description = p.description && <p className="sc-description">{p.description}</p>
  const variants = <Variants rows={p.variants} prices={prices} cameFromApp={cameFromApp} />
  const price = <span className="sc-price-tag">{formatPrice(p.price)}</span>

  const crumbs = (
    <nav className="sc-crumbs" aria-label="Навигация">
      <Link to="/">Главная</Link>
      <span aria-hidden="true">/</span>
      <Link to="/">Все товары</Link>
    </nav>
  )

  const below = (
    <>
      {design !== 'vitrina' && (
        <div className="sc-product__details">
          <Specs product={p} />
          <ProductReviews key={p.id} product={p} onChanged={onReviewsChanged} />
        </div>
      )}
      <Related productId={p.id} title={design === 'afisha' ? 'С этим товаром берут' : 'С этим товаром часто покупают'} />
      {design === 'vitrina' && <ProductReviews key={p.id} product={p} onChanged={onReviewsChanged} />}
    </>
  )

  if (design === 'vitrina') {
    return (
      <div className="sc-product sc-product--vitrina" aria-busy={busy}>
        {crumbs}
        <h1 className="sc-product__title">{p.title}</h1>
        <div className="sc-product__meta">
          <Rating product={p} />
          <span>Артикул {p.id}</span>
          <FavoriteToggle productId={p.id} className="sc-fav-text" withLabel />
        </div>
        <div className="sc-product__main">
          <Gallery product={p} />
          <div className="sc-product__info">
            {variants}
            {description}
            <Specs product={p} limit={6} />
          </div>
          <aside className="sc-product__buybox" aria-label="Покупка">
            {price}
            <BuyButtons product={p} />
            <StockLine product={p} />
            <DeliveryList methods={p.delivery_methods} />
          </aside>
        </div>
        {below}
      </div>
    )
  }

  // «Ночь» и «Афиша»: фото слева, справа — название, цена, варианты, покупка, условия
  return (
    <div className={`sc-product sc-product--${design}`} aria-busy={busy}>
      {crumbs}
      <div className="sc-product__main">
        <div className="sc-product__media">
          <Gallery product={p} />
          {design === 'night' && <FavoriteToggle productId={p.id} className="sc-fav sc-fav--corner" />}
        </div>
        <div className="sc-product__info">
          <div className="sc-product__meta">
            {design === 'afisha' && type && <span className="sc-product__type">{type}</span>}
            <span>Артикул {p.id}</span>
            {design === 'afisha' && <Rating product={p} />}
          </div>
          <h1 className="sc-product__title">{design === 'afisha' ? name : p.title}</h1>
          {design === 'night' && <Rating product={p} />}
          <div className="sc-product__price-row">{price}</div>
          {variants}
          <BuyButtons product={p} />
          <ul className="sc-facts">
            <li className="sc-facts__item">
              <span className="sc-facts__label">Наличие</span>
              <StockLine product={p} />
            </li>
            {p.delivery_methods.map((method) => (
              <li key={method.id} className="sc-facts__item">
                <span className="sc-facts__label">{method.kind === 'pickup' ? 'Самовывоз' : 'Курьер'}</span>
                <b>
                  {method.name} — {formatDeliveryPrice(method.price)}
                </b>
                <small>{deliveryNote(method)}</small>
              </li>
            ))}
          </ul>
          {description}
        </div>
      </div>
      {below}
    </div>
  )
}
