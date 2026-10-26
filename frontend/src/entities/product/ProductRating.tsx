import { formatRating, pluralize } from '@/shared/lib'

interface ProductRatingProps {
  /** Средняя оценка строкой из API ("4.75") */
  value: string
  count: number
}

/** Оценка в плитке товара: «★ 4,8 · 12 отзывов», без отзывов — серая звезда и «Нет отзывов». */
export function ProductRating({ value, count }: ProductRatingProps) {
  return (
    <span className="product-rating">
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        className={count > 0 ? 'product-rating__star' : 'product-rating__star product-rating__star--empty'}
      >
        <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" />
      </svg>
      {count > 0 ? (
        <>
          <b className="product-rating__value">{formatRating(value)}</b>
          <span aria-hidden="true">·</span>
          {pluralize(count, ['отзыв', 'отзыва', 'отзывов'])}
        </>
      ) : (
        'Нет отзывов'
      )}
    </span>
  )
}
