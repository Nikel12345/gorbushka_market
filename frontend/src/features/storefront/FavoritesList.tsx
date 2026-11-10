import type { ProductCard } from '@/shared/api'
import { EmptyState, LinkButton, Loader } from '@/shared/ui'
import { useFavorites } from './favorites'
import { useProductsByIds } from './hooks'
import { ShowcaseTile } from './ShowcaseTile'

/** Избранное: плитки сохранённых товаров (порядок — последний добавленный первым) */
export function FavoritesList() {
  const { ids } = useFavorites()
  const { products, loaded } = useProductsByIds(ids)
  const list = ids.flatMap((id): ProductCard[] => {
    const product = products.get(id)
    return product ? [product] : []
  })

  return (
    <section className="sc-favorites">
      <h1 className="sc-catalog-head__title">Избранное</h1>
      {ids.length === 0 ? (
        <EmptyState
          title="В избранном пока пусто"
          text="Нажмите на сердечко у товара — он появится здесь."
          action={<LinkButton to="/">Перейти в каталог</LinkButton>}
        />
      ) : !loaded && list.length === 0 ? (
        <Loader />
      ) : (
        <ul className="sc-grid">
          {list.map((product) => (
            <li key={product.id}>
              <ShowcaseTile product={product} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
