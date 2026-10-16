import { sellerApi, type Product, type ProductFieldsPayload } from '@/shared/api'

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
 * Сохраняет товар вместе с фото так, как их расставил продавец:
 * 1) удаляет убранные (освобождает место под лимит),
 * 2) PATCH полей + новые файлы (сервер добавит их в конец),
 * 3) если порядок отличается от нужного — PUT порядка (первое станет обложкой).
 */
export async function saveProductWithPhotos(
  shopId: number,
  product: Product,
  fields: ProductFieldsPayload,
  photos: PhotoItem[],
): Promise<Product> {
  const keptIds = new Set(photos.flatMap((photo) => (photo.kind === 'saved' ? [photo.id] : [])))
  for (const image of product.images) {
    if (!keptIds.has(image.id)) await sellerApi.deleteProductPhoto(shopId, product.id, image.id)
  }

  const updated = await sellerApi.updateProduct(shopId, product.id, { ...fields, images: newPhotoFiles(photos) })

  // Новые фото пришли в конце в том же порядке, в каком их отправили
  const createdIds = updated.images.filter((image) => !keptIds.has(image.id)).map((image) => image.id)
  let next = 0
  const wanted = photos.map((photo) => (photo.kind === 'saved' ? photo.id : createdIds[next++]))
  if (wanted.join() === updated.images.map((image) => image.id).join()) return updated

  const images = await sellerApi.reorderProductPhotos(shopId, product.id, wanted)
  return { ...updated, images, image: images[0]?.url ?? null }
}
