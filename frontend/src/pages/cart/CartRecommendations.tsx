import { useId } from 'react'
import { useNavigationType } from 'react-router'
import { ProductRating, ProductTile } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { cartApi, getErrorMessage } from '@/shared/api'
import { useCursorFeed } from '@/shared/lib'
import { Button, InfiniteScrollTrigger, Loader } from '@/shared/ui'

const loadRecommendations = (cursor: string | undefined, signal: AbortSignal) =>
  cartApi.recommendations(cursor, { signal })

/**
 * «Рекомендуем» под товарами корзины: аксессуары к ним, потом лента главной — бесконечной
 * прокруткой, как на главной. Блок второстепенный: пока первая порция не пришла или не удалась — его нет.
 * Список собирается по корзине при входе на страницу; то, что положили в корзину отсюда,
 * остаётся на месте (с выбранным количеством), чтобы лента не прыгала.
 */
export function CartRecommendations() {
  const titleId = useId()
  // «Назад» со страницы товара — та же лента, и ScrollRestoration вернёт прокрутку на ту же плитку
  const navigationType = useNavigationType()
  const feed = useCursorFeed(loadRecommendations, { key: 'cart-recommendations', restore: navigationType === 'POP' })

  if (feed.initial || feed.failed === 'replace' || feed.items.length === 0) return null

  return (
    <section className="cart-recommendations" aria-labelledby={titleId}>
      <h2 id={titleId} className="cart-recommendations__title">
        Рекомендуем
      </h2>
      <ul className="product-grid">
        {feed.items.map((product) => (
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

      <InfiniteScrollTrigger
        onReach={feed.loadMore}
        disabled={!feed.hasMore || feed.loading !== null || feed.failed !== null}
      />
      <div className="cart-recommendations__footer">
        {feed.loading === 'more' && <Loader label="Загружаем ещё…" />}
        {feed.failed === 'more' && (
          <div className="cart-recommendations__error" role="alert">
            <span>Не удалось загрузить товары: {getErrorMessage(feed.error)}</span>
            <Button onClick={feed.retry}>Повторить</Button>
          </div>
        )}
        {!feed.hasMore && feed.loading === null && <span className="ui-muted">Больше товаров нет</span>}
      </div>
    </section>
  )
}
