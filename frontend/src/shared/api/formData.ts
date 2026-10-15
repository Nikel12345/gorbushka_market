/**
 * Объект → multipart/form-data для загрузки файлов.
 * undefined и null пропускаются, файлы (Blob/File) идут как есть, массив — повторяющимся
 * полем (key=1&key=2, так его читает DRF), остальное — строкой.
 */
export function toFormData(data: object): FormData {
  const form = new FormData()
  for (const [key, value] of Object.entries(data) as [string, unknown][]) {
    if (value === undefined || value === null) continue
    const values: unknown[] = Array.isArray(value) ? value : [value]
    for (const item of values) form.append(key, item instanceof Blob ? item : String(item))
  }
  return form
}
