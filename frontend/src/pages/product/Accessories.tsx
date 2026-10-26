import { useCallback } from 'react'
import { catalogApi } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { ProductShelf } from './ProductShelf'

/**
 * «Аксессуары» — список, заданный менеджером (у вариантов одной группы общий).
 * Как и «Часто покупают»: пока грузится, если список пуст или запрос не удался — блока нет.
 */
export function Accessories({ productId }: { productId: number }) {
  const load = useCallback((signal: AbortSignal) => catalogApi.accessories(productId, { signal }), [productId])
  const products = useRequest(load)

  // Временно под названием «Часто покупают» — см. ProductPage
  return <ProductShelf title="С этим товаром часто покупают" products={products.data} />
}
