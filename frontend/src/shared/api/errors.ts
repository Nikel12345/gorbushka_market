import { ApiError } from './client'

/** Ошибки валидации в формате DRF: { field: ["msg", ...], non_field_errors: [...], detail: "..." } */
export type FieldErrors = Record<string, string[]>

export function getFieldErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiError)) {
    return { non_field_errors: ['Не удалось связаться с сервером. Попробуйте позже.'] }
  }

  if (error.status === 429) {
    return { non_field_errors: ['Слишком много попыток. Подождите немного и попробуйте снова.'] }
  }

  const data = error.data
  if (data && typeof data === 'object') {
    const result: FieldErrors = {}
    for (const [key, value] of Object.entries(data)) {
      const field = key === 'detail' ? 'non_field_errors' : key
      result[field] = Array.isArray(value) ? value.map(String) : [String(value)]
    }
    return result
  }

  return { non_field_errors: ['Что-то пошло не так. Попробуйте позже.'] }
}

/** Одно сообщение для ошибки загрузки данных (не формы). */
export function getErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Не удалось связаться с сервером. Попробуйте позже.'
  }

  switch (error.status) {
    case 401:
    case 403:
      return 'Нет доступа. Возможно, сессия истекла — войдите заново.'
    case 404:
      return 'Не найдено.'
    case 429:
      return 'Слишком много запросов. Подождите немного и попробуйте снова.'
  }

  const detail = (error.data as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail

  return error.status >= 500
    ? 'Ошибка на сервере. Попробуйте позже.'
    : 'Что-то пошло не так. Попробуйте позже.'
}
