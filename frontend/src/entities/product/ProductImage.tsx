import { useState, type ReactNode } from 'react'
import placeholderUrl from './product-placeholder.svg'
import './ProductImage.css'

interface ProductImageProps {
  src?: string | null
  alt: string
  className?: string
  /** Плашки поверх картинки (например, «Нет в наличии») */
  children?: ReactNode
}

/** Квадратное фото товара. Нет фото или оно не загрузилось — заглушка. */
export function ProductImage({ src, alt, className, children }: ProductImageProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  const hasImage = Boolean(src) && failedSrc !== src

  const classes = ['product-image', hasImage ? '' : 'product-image--placeholder', className].filter(Boolean).join(' ')

  return (
    <div className={classes}>
      {hasImage ? (
        <img src={src!} alt={alt} loading="lazy" onError={() => setFailedSrc(src!)} />
      ) : (
        <img src={placeholderUrl} alt="" />
      )}
      {children}
    </div>
  )
}
