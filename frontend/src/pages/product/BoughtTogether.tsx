import { useCallback } from 'react'
import { ProductRating, ProductTile } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { catalogApi } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import './BoughtTogether.css'

/**
 * «С этим товаром часто покупают» — плитки как в ленте, с кнопкой «в корзину».
 * Блок второстепенный: пока грузится, если данных нет или запрос не удался — его просто нет.
 * При переходе на вариант прежние плитки видны, пока не придут новые.
 */
export function BoughtTogether({ productId }: { productId: number }) {
  const load = useCallback((signal: AbortSignal) => catalogApi.boughtTogether(productId, { signal }), [productId])
  const products = useRequest(load)

  if (!products.data?.length) return null

  return (
    <section className="bought-together" aria-labelledby="bought-together-title">
      <h2 id="bought-together-title" className="bought-together__title">
        С этим товаром часто покупают
      </h2>
      <ul className="product-grid bought-together__grid">
        {products.data.map((product) => (
          <li key={product.id}>
            <ProductTile
              product={product}
              to={`/products/${product.id}`}
              badge={!product.in_stock && 'Нет в наличии'}
              meta={<ProductRating value={product.rating} count={product.reviews_count} />}
              action={<CartControl productId={product.id} variant="compact" canBuy={product.in_stock} />}
            />
          </li>
        ))}
      </ul>
    </section>
  )
}
