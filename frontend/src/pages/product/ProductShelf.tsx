import { useId } from 'react'
import { ProductRating, ProductTile } from '@/entities/product'
import { CartControl } from '@/features/cart'
import type { ProductCard } from '@/shared/api'
import './ProductShelf.css'

/** Плиток в строке на широком экране; больше — строка листается вбок */
const ROW_SIZE = 5

/**
 * Полка товаров под карточкой («Аксессуары», «Часто покупают»): плитки как в ленте,
 * с кнопкой «в корзину», одной строкой. Пустой список — полки нет.
 */
export function ProductShelf({ title, products }: { title: string; products: ProductCard[] | null | undefined }) {
  const titleId = useId()

  if (!products?.length) return null

  const gridClass = `product-grid product-shelf__grid${products.length > ROW_SIZE ? ' product-shelf__grid--scroll' : ''}`

  return (
    <section className="product-shelf" aria-labelledby={titleId}>
      <h2 id={titleId} className="product-shelf__title">
        {title}
      </h2>
      <ul className={gridClass}>
        {products.map((product) => (
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
