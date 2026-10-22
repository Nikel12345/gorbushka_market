import { adminApi, type Product, type ProductFieldsPayload } from '@/shared/api'

/** Фото в форме товара: уже сохранённое (есть id) или выбранное, но ещё не загруженное */
export type PhotoItem =
  | { key: string; kind: 'saved'; id: number; url: string | null }
  | { key: string; kind: 'new'; file: File }

let newKey = 0

export function photosFromProduct(product: Product): PhotoItem[] {
  return product.images.map((image) => ({ key: `saved-${image.id}`, kind: 'saved', id: image.id, url: image.url }))
}

export function photosFromFiles(files: File[]): PhotoItem[] {
  return files.map((file) => ({ key: `new-${++newKey}`, kind: 'new', file }))
}

export function newPhotoFiles(photos: PhotoItem[]): File[] {
  return photos.flatMap((photo) => (photo.kind === 'new' ? [photo.file] : []))
}

/**
 * Сохраняет товар вместе с фото так, как их расставили в форме:
 * 1) удаляет убранные (освобождает место под лимит),
 * 2) PATCH полей — JSON: в multipart не передать «убрать из группы» (null) и пустой набор характеристик,
 * 3) новые файлы — отдельным PATCH (сервер добавит их в конец),
 * 4) если порядок отличается от нужного — PUT порядка (первое станет обложкой).
 */
export async function saveProductWithPhotos(
  product: Product,
  fields: ProductFieldsPayload,
  photos: PhotoItem[],
): Promise<Product> {
  const keptIds = new Set(photos.flatMap((photo) => (photo.kind === 'saved' ? [photo.id] : [])))
  for (const image of product.images) {
    if (!keptIds.has(image.id)) await adminApi.deleteProductPhoto(product.id, image.id)
  }

  let updated = await adminApi.updateProduct(product.id, fields)
  const files = newPhotoFiles(photos)
  if (files.length > 0) updated = await adminApi.updateProduct(product.id, { images: files })

  // Новые фото пришли в конце в том же порядке, в каком их отправили
  const createdIds = updated.images.filter((image) => !keptIds.has(image.id)).map((image) => image.id)
  let next = 0
  const wanted = photos.map((photo) => (photo.kind === 'saved' ? photo.id : createdIds[next++]))
  if (wanted.join() === updated.images.map((image) => image.id).join()) return updated

  const images = await adminApi.reorderProductPhotos(product.id, wanted)
  return { ...updated, images, image: images[0]?.url ?? null }
}
