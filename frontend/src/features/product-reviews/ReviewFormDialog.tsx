import { useState, type FormEvent } from 'react'
import {
  getFieldErrors,
  REVIEW_TEXT_MAX_LENGTH,
  reviewsApi,
  type FieldErrors,
  type Review,
  type ReviewPayload,
} from '@/shared/api'
import { Button, Dialog, Field, FieldError } from '@/shared/ui'
import { StarShape } from './RatingStars'

const FORM_ID = 'review-form'
const RATING_LABELS = ['Ужасно', 'Плохо', 'Нормально', 'Хорошо', 'Отлично']

interface ReviewFormDialogProps {
  productId: number
  productTitle: string
  /** Нет — новый отзыв */
  review?: Review
  onClose: () => void
  onSaved: (review: Review) => void
}

/** Оценка и текст отзыва: достоинства, недостатки, комментарий — достаточно одного. */
export function ReviewFormDialog({ productId, productTitle, review, onClose, onSaved }: ReviewFormDialogProps) {
  const [rating, setRating] = useState(review?.rating ?? 0)
  const [hovered, setHovered] = useState(0)
  const [pros, setPros] = useState(review?.pros ?? '')
  const [cons, setCons] = useState(review?.cons ?? '')
  const [comment, setComment] = useState(review?.comment ?? '')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)

  const shownRating = hovered || rating

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const payload: ReviewPayload = { rating, pros: pros.trim(), cons: cons.trim(), comment: comment.trim() }
    const localErrors: FieldErrors = {}
    if (!rating) localErrors.rating = ['Поставьте оценку.']
    if (!payload.pros && !payload.cons && !payload.comment) {
      localErrors.non_field_errors = ['Напишите достоинства, недостатки или комментарий.']
    }
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setSaving(true)
    try {
      onSaved(review ? await reviewsApi.update(review.id, payload) : await reviewsApi.create(productId, payload))
    } catch (error) {
      setErrors(getFieldErrors(error))
      setSaving(false)
    }
  }

  const text = (label: string, value: string, onChange: (value: string) => void, field: keyof ReviewPayload) => (
    <Field label={label} errors={errors[field]}>
      <textarea
        className="ui-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(errors[field])}
        maxLength={REVIEW_TEXT_MAX_LENGTH}
        rows={3}
      />
    </Field>
  )

  return (
    <Dialog
      title={review ? 'Ваш отзыв' : 'Отзыв о товаре'}
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={saving}>
            {saving ? 'Сохраняем…' : review ? 'Сохранить' : 'Опубликовать'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="ui-form" onSubmit={handleSubmit} noValidate>
        <p className="review-form__product">{productTitle}</p>

        <fieldset className="review-form__rating">
          <legend className="ui-field__label">Оценка</legend>
          <div className="rating-input" onMouseLeave={() => setHovered(0)}>
            {RATING_LABELS.map((label, index) => {
              const value = index + 1
              return (
                <label
                  key={value}
                  className={value <= shownRating ? 'rating-input__star rating-input__star--on' : 'rating-input__star'}
                  onMouseEnter={() => setHovered(value)}
                >
                  <input
                    type="radio"
                    name="rating"
                    className="ui-sr-only"
                    value={value}
                    checked={rating === value}
                    onChange={() => setRating(value)}
                    aria-invalid={Boolean(errors.rating)}
                    data-autofocus={value === (rating || 1) ? true : undefined}
                  />
                  <StarShape />
                  <span className="ui-sr-only">{`${value} из 5 — ${label}`}</span>
                </label>
              )
            })}
            <span className="rating-input__caption" aria-hidden="true">
              {shownRating ? RATING_LABELS[shownRating - 1] : 'Выберите оценку'}
            </span>
          </div>
          <FieldError messages={errors.rating} />
        </fieldset>

        {text('Достоинства', pros, setPros, 'pros')}
        {text('Недостатки', cons, setCons, 'cons')}
        {text('Комментарий', comment, setComment, 'comment')}
        <span className="ui-field__hint">Достаточно заполнить одно из трёх полей.</span>
        <FieldError messages={errors.non_field_errors} />
      </form>
    </Dialog>
  )
}
