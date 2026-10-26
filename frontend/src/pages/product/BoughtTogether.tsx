import { useCallback } from 'react'
import { catalogApi } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { ProductShelf } from './ProductShelf'

/**
 * «С этим товаром часто покупают».
 * Блок второстепенный: пока грузится, если данных нет или запрос не удался — его просто нет.
 * При переходе на вариант прежние плитки видны, пока не придут новые.
 */
export function BoughtTogether({ productId }: { productId: number }) {
  const load = useCallback((signal: AbortSignal) => catalogApi.boughtTogether(productId, { signal }), [productId])
  const products = useRequest(load)

  return <ProductShelf title="С этим товаром часто покупают" products={products.data} />
}
