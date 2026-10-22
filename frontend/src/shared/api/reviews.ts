import { apiRequest, type ApiRequestInit } from './client'
import { withQuery } from './query'
import type { CursorPage } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Отзыв о товаре (ReviewSerializer) — на витрине и у автора */
export interface Review {
  id: number
  product_id: number
  product_title: string
  /** Имя автора, без имени — «Покупатель». Email не приходит */
  author_name: string
  /** От 1 до 5 */
  rating: number
  /** Достоинства, недостатки, комментарий: хотя бы одно не пустое */
  pros: string
  cons: string
  comment: string
  created_at: string
  updated_at: string
}

/** Сортировки отзывов (ReviewPagination.sort_options) */
export const REVIEW_SORTS = ['new', 'rating_desc', 'rating_asc'] as const
export type ReviewSort = (typeof REVIEW_SORTS)[number]

export interface ReviewListParams {
  /** Только с этой оценкой */
  rating?: number
  sort?: ReviewSort
  /** Позиция из next_cursor предыдущей порции; без него — с начала */
  cursor?: string
  page_size?: number
}

/** Оценка и текст; товар задаётся только при создании */
export interface ReviewPayload {
  rating: number
  pros: string
  cons: string
  comment: string
}

/** Длина каждого из трёх текстов (reviews.models.TEXT_MAX_LENGTH) */
export const REVIEW_TEXT_MAX_LENGTH = 2000

const MY_REVIEWS = '/me/reviews/'

export const reviewsApi = {
  /** Отзывы о товаре на продаже; 404 — товар снят с продажи */
  listForProduct: (
    productId: number,
    { rating, sort, cursor, page_size }: ReviewListParams = {},
    options?: RequestOptions,
  ) =>
    apiRequest<CursorPage<Review>>(
      withQuery(`/catalog/products/${productId}/reviews/`, { rating, sort, cursor, page_size }),
      options,
    ),

  /** Отзыв текущего пользователя на товар; null — ещё не писал */
  getMine: (productId: number, options?: RequestOptions) =>
    apiRequest<CursorPage<Review>>(withQuery(MY_REVIEWS, { product: productId }), options).then(
      (page) => page.results[0] ?? null,
    ),

  /** 400 code=review_exists — отзыв на этот товар уже есть, его можно изменить */
  create: (productId: number, payload: ReviewPayload) =>
    apiRequest<Review>(MY_REVIEWS, { method: 'POST', json: { product_id: productId, ...payload } }),

  update: (reviewId: number, payload: Partial<ReviewPayload>) =>
    apiRequest<Review>(`${MY_REVIEWS}${reviewId}/`, { method: 'PATCH', json: payload }),

  remove: (reviewId: number) => apiRequest<null>(`${MY_REVIEWS}${reviewId}/`, { method: 'DELETE' }),
}
