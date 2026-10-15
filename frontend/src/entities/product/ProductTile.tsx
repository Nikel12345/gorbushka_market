import type { ReactNode } from 'react'
import { Link, type To } from 'react-router'
import { formatPrice } from '@/shared/lib'
import { ProductImage } from './ProductImage'
import './ProductTile.css'

interface ProductTileProps {
  product: { title: string; price: string; image: string | null }
  /** Куда ведёт плитка; без него — просто карточка без перехода */
  to?: To
  /** Плашка поверх фото, например «Нет в наличии» */
  badge?: ReactNode
  /** Строка под названием: остаток, магазин, дата */
  meta?: ReactNode
}

/** Плитка товара в сетке (.product-grid): фото, цена, название. */
export function ProductTile({ product, to, badge, meta }: ProductTileProps) {
  const content = (
    <>
      <ProductImage src={product.image} alt={product.title}>
        {badge && <span className="product-tile__badge">{badge}</span>}
      </ProductImage>
      <span className="product-tile__body">
        <span className="product-tile__price">{formatPrice(product.price)}</span>
        <span className="product-tile__title">{product.title}</span>
        {meta && <span className="product-tile__meta">{meta}</span>}
      </span>
    </>
  )

  return to ? (
    <Link className="product-tile product-tile--link" to={to}>
      {content}
    </Link>
  ) : (
    <div className="product-tile">{content}</div>
  )
}
