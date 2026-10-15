/** Ответ DRF PageNumberPagination */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Ответ курсорной пагинации бэкенда (apps/core/pagination.py) — для бесконечных лент */
export interface CursorPage<T> {
  /** null — лента закончилась */
  next_cursor: string | null
  results: T[]
}
