import { formatRating } from '@/shared/lib'

const STAR_PATH = 'M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z'

export function StarShape() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={STAR_PATH} />
    </svg>
  )
}

function StarRow() {
  return (
    <>
      {[1, 2, 3, 4, 5].map((n) => (
        <StarShape key={n} />
      ))}
    </>
  )
}

interface RatingStarsProps {
  /** От 0 до 5, дробная закрашивается частично: 4,5 — четыре с половиной звезды */
  value: number
  size?: 'default' | 'large'
}

/** Оценка звёздами: серые снизу, закрашенные поверх — обрезаны по доле оценки. */
export function RatingStars({ value, size = 'default' }: RatingStarsProps) {
  const share = (Math.min(Math.max(value, 0), 5) / 5) * 100
  return (
    <span
      className={size === 'large' ? 'rating-stars rating-stars--large' : 'rating-stars'}
      role="img"
      aria-label={`Оценка ${formatRating(value)} из 5`}
    >
      <span className="rating-stars__row">
        <StarRow />
      </span>
      <span className="rating-stars__row rating-stars__row--fill" style={{ width: `${share}%` }}>
        <StarRow />
      </span>
    </span>
  )
}
