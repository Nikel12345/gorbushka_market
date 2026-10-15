/** Номер страницы из ?page=, по умолчанию 1. */
export function parsePage(value: string | null): number {
  const page = Number(value)
  return Number.isInteger(page) && page > 1 ? page : 1
}

/** Копия search params с изменёнными значениями; пустое значение удаляет ключ. */
export function updateSearchParams(
  current: URLSearchParams,
  changes: Record<string, string | number | null | undefined>,
): URLSearchParams {
  const next = new URLSearchParams(current)
  for (const [key, value] of Object.entries(changes)) {
    if (value === null || value === undefined || value === '') next.delete(key)
    else next.set(key, String(value))
  }
  return next
}
