export type QueryParams = Record<string, string | number | undefined>

/** Добавляет к пути query-строку, пропуская пустые значения. */
export function withQuery(path: string, params: QueryParams): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}
