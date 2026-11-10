import { Link } from 'react-router'
import { ProductImage } from '@/entities/product'
import { CartControl } from '@/features/cart'
import type { ProductCard } from '@/shared/api'
import { formatPrice, formatRating, pluralize } from '@/shared/lib'
import { FavoriteToggle } from './FavoriteToggle'
import { StarIcon } from './icons'

/**
 * Плитка товара «витринных» вариантов (как в макетах): фото с сердечком, цена, название, оценка,
 * «Самовывоз сегодня» («Витрина») и кнопка «В корзину» во всю ширину.
 */
export function ShowcaseTile({ product: p }: { product: ProductCard }) {
  const to = `/products/${p.id}`

  return (
    <article className="sc-tile">
      <div className="sc-tile__media">
        {/* Фото — та же ссылка, что и название: для клавиатуры и чтения экрана достаточно одной */}
        <Link to={to} className="sc-tile__image" tabIndex={-1} aria-hidden="true">
          <ProductImage src={p.image} alt="" />
        </Link>
        <FavoriteToggle productId={p.id} />
        {!p.in_stock && <span className="sc-tile__badge">Нет в наличии</span>}
      </div>
      <span className="sc-tile__price">{formatPrice(p.price)}</span>
      <Link to={to} className="sc-tile__title">
        {p.title}
      </Link>
      <span className="sc-tile__rating">
        <StarIcon empty={p.reviews_count === 0} />
        {p.reviews_count > 0 ? (
          <>
            <b>{formatRating(p.rating)}</b>
            <span>· {pluralize(p.reviews_count, ['отзыв', 'отзыва', 'отзывов'])}</span>
          </>
        ) : (
          'Нет отзывов'
        )}
      </span>
      {p.in_stock && <span className="sc-tile__pickup">Самовывоз сегодня</span>}
      <div className="sc-tile__cart">
        {p.in_stock ? (
          <CartControl productId={p.id} variant="compact" canBuy />
        ) : (
          <button type="button" className="sc-tile__unavailable" disabled>
            Нет в наличии
          </button>
        )}
      </div>
    </article>
  )
}
