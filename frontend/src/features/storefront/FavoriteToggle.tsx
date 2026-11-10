import { useFavorites } from './favorites'
import { HeartIcon } from './icons'

/** Сердечко «в избранное»: на фото плитки и на странице товара */
export function FavoriteToggle({
  productId,
  className = 'sc-fav',
  withLabel = false,
}: {
  productId: number
  className?: string
  /** Подпись рядом с сердечком («В избранное» / «В избранном») */
  withLabel?: boolean
}) {
  const { has, toggle } = useFavorites()
  const active = has(productId)
  const label = active ? 'Убрать из избранного' : 'Добавить в избранное'

  return (
    <button
      type="button"
      className={active ? `${className} ${className}--active` : className}
      aria-pressed={active}
      aria-label={withLabel ? undefined : label}
      title={label}
      onClick={(event) => {
        // Плитка — ссылка рядом: клик по сердечку не открывает товар
        event.preventDefault()
        event.stopPropagation()
        toggle(productId)
      }}
    >
      <HeartIcon filled={active} />
      {withLabel && <span>{active ? 'В избранном' : 'В избранное'}</span>}
    </button>
  )
}
