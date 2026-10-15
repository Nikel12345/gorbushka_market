/**
 * Объект → multipart/form-data для загрузки файлов.
 * undefined и null пропускаются, файлы (Blob/File) идут как есть, остальное — строкой.
 */
export function toFormData(data: object): FormData {
  const form = new FormData()
  for (const [key, value] of Object.entries(data) as [string, unknown][]) {
    if (value === undefined || value === null) continue
    form.append(key, value instanceof Blob ? value : String(value))
  }
  return form
}
