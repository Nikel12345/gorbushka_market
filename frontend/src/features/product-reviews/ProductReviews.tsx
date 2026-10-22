import { useCallback, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { getErrorMessage, reviewsApi, type ProductCard, type Review, type ReviewSort } from '@/shared/api'
import { formatDate, formatRating, pluralize, useCursorFeed, useRequest } from '@/shared/lib'
import { Button, Chip, Dialog, EmptyState, ErrorState, FieldError, Loader } from '@/shared/ui'
import { RatingStars, StarShape } from './RatingStars'
import { ReviewFormDialog } from './ReviewFormDialog'
import './ProductReviews.css'

/** id блока: к нему ведёт плашка с оценкой вверху страницы товара */
export const REVIEWS_ANCHOR = 'reviews'

const PAGE_SIZE = 10

const SORT_OPTIONS: { value: ReviewSort; label: string }[] = [
  { value: 'new', label: 'Сначала новые' },
  { value: 'rating_desc', label: 'Сначала с высокой оценкой' },
  { value: 'rating_asc', label: 'Сначала с низкой оценкой' },
]

interface ProductReviewsProps {
  product: Pick<ProductCard, 'id' | 'title' | 'rating' | 'reviews_count'>
  /** Отзыв добавили, изменили или удалили — у товара пересчитались оценка и число отзывов */
  onChanged: () => void
}

/**
 * Отзывы о товаре: средняя оценка, список с фильтром по оценке и сортировкой («Показать ещё»),
 * свой отзыв — написать, изменить, удалить. У каждого варианта товара отзывы свои.
 */
export function ProductReviews({ product, onChanged }: ProductReviewsProps) {
  const { user, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sort, setSort] = useState<ReviewSort>('new')
  const [rating, setRating] = useState<number | null>(null)
  const [editing, setEditing] = useState<Review | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Review | null>(null)

  const productId = product.id
  const userId = user?.id
  const loadMine = useCallback(
    (signal: AbortSignal) => (userId === undefined ? Promise.resolve(null) : reviewsApi.getMine(productId, { signal })),
    [productId, userId],
  )
  const mine = useRequest(loadMine)
  const myReview = mine.data ?? null

  const load = useCallback(
    (cursor: string | undefined, signal: AbortSignal) =>
      reviewsApi.listForProduct(
        productId,
        { rating: rating ?? undefined, sort, cursor, page_size: PAGE_SIZE },
        { signal },
      ),
    [productId, rating, sort],
  )
  const feed = useCursorFeed(load)

  function handleChanged() {
    setEditing(null)
    setDeleting(null)
    mine.reload()
    feed.reload()
    onChanged()
  }

  function write() {
    if (status === 'anonymous') {
      navigate('/login', { state: { from: location.pathname + location.search } })
      return
    }
    setEditing(myReview ?? 'new')
  }

  // Пока не ясно, писал ли пользователь отзыв, кнопка ждёт: иначе «Написать» сменится на «Изменить»
  const mineUnknown = status === 'loading' || (userId !== undefined && mine.data === undefined && !mine.error)
  const count = product.reviews_count

  let list
  if (feed.failed === 'replace') {
    list = <ErrorState message={getErrorMessage(feed.error)} onRetry={feed.retry} />
  } else if (feed.initial) {
    list = <Loader />
  } else if (feed.items.length === 0) {
    list =
      rating === null ? (
        <EmptyState
          title="Отзывов пока нет"
          text="Пользовались этим товаром? Расскажите о нём — это поможет другим с выбором."
        />
      ) : (
        <EmptyState
          title={`Отзывов с оценкой ${rating} нет`}
          action={<Button onClick={() => setRating(null)}>Показать все отзывы</Button>}
        />
      )
  } else {
    list = (
      <>
        <ul className="product-reviews__list" aria-busy={feed.loading === 'replace'}>
          {feed.items.map((review) => (
            <li key={review.id}>
              <ReviewItem
                review={review}
                own={review.id === myReview?.id}
                onEdit={() => setEditing(review)}
                onDelete={() => setDeleting(review)}
              />
            </li>
          ))}
        </ul>
        {feed.failed === 'more' && (
          <div className="product-reviews__more-error" role="alert">
            Не удалось загрузить отзывы: {getErrorMessage(feed.error)}
          </div>
        )}
        {feed.hasMore && (
          <div className="product-reviews__footer">
            <Button onClick={feed.failed === 'more' ? feed.retry : feed.loadMore} disabled={feed.loading !== null}>
              {feed.loading === 'more' ? 'Загружаем…' : feed.failed === 'more' ? 'Повторить' : 'Показать ещё'}
            </Button>
          </div>
        )}
      </>
    )
  }

  return (
    <section id={REVIEWS_ANCHOR} className="product-reviews" aria-labelledby={`${REVIEWS_ANCHOR}-title`}>
      <header className="product-reviews__head">
        <h2 id={`${REVIEWS_ANCHOR}-title`} className="product-reviews__title">
          Отзывы
          {count > 0 && <span className="product-reviews__count">{count}</span>}
        </h2>
        <Button variant={myReview ? 'default' : 'primary'} onClick={write} disabled={mineUnknown}>
          {myReview ? 'Изменить мой отзыв' : 'Написать отзыв'}
        </Button>
      </header>

      {count > 0 && (
        <div className="product-reviews__summary">
          <span className="product-reviews__average">{formatRating(product.rating)}</span>
          <div className="product-reviews__summary-text">
            <RatingStars value={Number(product.rating)} size="large" />
            <span className="ui-muted">{`из 5 · ${pluralize(count, ['отзыв', 'отзыва', 'отзывов'])}`}</span>
          </div>
        </div>
      )}

      {count > 0 && (
        <div className="product-reviews__toolbar">
          <div className="product-reviews__ratings" role="group" aria-label="Оценка">
            {[null, 5, 4, 3, 2, 1].map((value) => (
              <button
                key={value ?? 'all'}
                type="button"
                className={
                  value === rating ? 'product-reviews__rating product-reviews__rating--active' : 'product-reviews__rating'
                }
                aria-pressed={value === rating}
                onClick={() => setRating(value)}
              >
                {value === null ? (
                  'Все'
                ) : (
                  <>
                    {value} <StarShape />
                  </>
                )}
              </button>
            ))}
          </div>
          <select
            className="ui-input product-reviews__sort"
            value={sort}
            onChange={(event) => setSort(event.target.value as ReviewSort)}
            aria-label="Порядок отзывов"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {list}

      {editing && (
        <ReviewFormDialog
          productId={productId}
          productTitle={product.title}
          review={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={handleChanged}
        />
      )}
      {deleting && (
        <DeleteReviewDialog review={deleting} onClose={() => setDeleting(null)} onDeleted={handleChanged} />
      )}
    </section>
  )
}

interface ReviewItemProps {
  review: Review
  /** Отзыв текущего пользователя: его можно изменить и удалить */
  own: boolean
  onEdit: () => void
  onDelete: () => void
}

function ReviewItem({ review, own, onEdit, onDelete }: ReviewItemProps) {
  return (
    <article className="review">
      <header className="review__head">
        <span className="review__author">{review.author_name}</span>
        {own && <Chip tone="info">Ваш отзыв</Chip>}
        <time className="review__date" dateTime={review.created_at}>
          {formatDate(review.created_at)}
        </time>
      </header>
      <RatingStars value={review.rating} />
      <ReviewText title="Достоинства" text={review.pros} />
      <ReviewText title="Недостатки" text={review.cons} />
      <ReviewText title="Комментарий" text={review.comment} />
      {own && (
        <div className="review__actions">
          <Button variant="text" onClick={onEdit}>
            Изменить
          </Button>
          <Button variant="text" onClick={onDelete}>
            Удалить
          </Button>
        </div>
      )}
    </article>
  )
}

function ReviewText({ title, text }: { title: string; text: string }) {
  if (!text) return null
  return (
    <div className="review__text">
      <span className="review__text-title">{title}</span>
      <p>{text}</p>
    </div>
  )
}

function DeleteReviewDialog({
  review,
  onClose,
  onDeleted,
}: {
  review: Review
  onClose: () => void
  onDeleted: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  async function handleDelete() {
    setBusy(true)
    setError(undefined)
    try {
      await reviewsApi.remove(review.id)
      onDeleted()
    } catch (err) {
      setError(getErrorMessage(err))
      setBusy(false)
    }
  }

  return (
    <Dialog
      title="Удалить отзыв?"
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={busy} data-autofocus>
            {busy ? 'Удаляем…' : 'Удалить'}
          </Button>
        </>
      }
    >
      <p className="review-delete__text">Отзыв пропадёт со страницы товара, оценка товара пересчитается без него.</p>
      <FieldError messages={error ? [error] : undefined} />
    </Dialog>
  )
}
