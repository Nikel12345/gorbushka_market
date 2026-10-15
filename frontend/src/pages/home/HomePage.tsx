import { useCallback } from 'react'
import { useLocation, useNavigationType, useSearchParams } from 'react-router'
import { ProductTile } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { getProductFilterErrors, ProductFiltersPanel, useProductFilters } from '@/features/product-filters'
import { catalogApi, getErrorMessage, PRODUCT_SORTS, type ProductSort } from '@/shared/api'
import { updateSearchParams, useCursorFeed } from '@/shared/lib'
import {
  Button,
  EmptyState,
  ErrorState,
  InfiniteScrollTrigger,
  LinearProgress,
  Loader,
  SidebarLayout,
} from '@/shared/ui'
import './HomePage.css'

const SORT_LABELS: Record<ProductSort, string> = {
  new: 'Сначала новые',
  price_asc: 'Сначала дешёвые',
  price_desc: 'Сначала дорогие',
}
const DEFAULT_SORT: ProductSort = 'new'

function parseSort(value: string | null): ProductSort {
  return PRODUCT_SORTS.find((sort) => sort === value) ?? DEFAULT_SORT
}

/** Главная: лента товаров всех магазинов. Фильтры слева, поиск — в шапке (тот же ?q=), подгрузка при прокрутке. */
export function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { filters, setFilters, resetFilters, activeCount } = useProductFilters()
  const sort = parseSort(searchParams.get('sort'))

  const load = useCallback(
    (cursor: string | undefined, signal: AbortSignal) => catalogApi.feed({ ...filters, sort, cursor }, { signal }),
    [filters, sort],
  )
  // «Назад» со страницы товара — показываем уже загруженную ленту, и ScrollRestoration
  // возвращает прокрутку на ту же плитку. Новые фильтры (переход вперёд) — грузим заново, с начала страницы.
  const { search } = useLocation()
  const navigationType = useNavigationType()
  const feed = useCursorFeed(load, { key: search, restore: navigationType === 'POP' })

  function changeSort(next: ProductSort) {
    setSearchParams((prev) => updateSearchParams(prev, { sort: next === DEFAULT_SORT ? null : next }))
  }

  const refreshing = feed.loading === 'replace' && !feed.initial
  const filterErrors = feed.failed === 'replace' ? getProductFilterErrors(feed.error) : undefined

  let content
  if (feed.failed === 'replace') {
    content = filterErrors ? (
      <EmptyState
        title="Проверьте фильтры"
        text="Некоторые значения не подходят — подробности в панели слева."
        action={<Button onClick={resetFilters}>Сбросить фильтры</Button>}
      />
    ) : (
      <ErrorState message={getErrorMessage(feed.error)} onRetry={feed.retry} />
    )
  } else if (feed.initial) {
    content = <Loader />
  } else if (feed.items.length === 0) {
    content =
      activeCount > 0 ? (
        <EmptyState
          title="Ничего не найдено"
          text="Попробуйте изменить запрос или условия фильтров."
          action={<Button onClick={resetFilters}>Сбросить фильтры</Button>}
        />
      ) : (
        <EmptyState title="Товаров пока нет" text="Загляните позже — магазины скоро что-нибудь выставят." />
      )
  } else {
    content = (
      <>
        <ul className={refreshing ? 'product-grid product-grid--dimmed' : 'product-grid'}>
          {feed.items.map((product) => (
            <li key={product.id}>
              <ProductTile
                product={product}
                to={`/products/${product.id}`}
                badge={!product.in_stock && 'Нет в наличии'}
                meta={product.shop.name}
                action={<CartControl productId={product.id} variant="compact" canBuy={product.in_stock} />}
              />
            </li>
          ))}
        </ul>

        <InfiniteScrollTrigger
          onReach={feed.loadMore}
          disabled={!feed.hasMore || feed.loading !== null || feed.failed !== null}
        />
        <div className="home-feed__footer">
          {feed.loading === 'more' && <Loader label="Загружаем ещё…" />}
          {feed.failed === 'more' && (
            <div className="home-feed__more-error" role="alert">
              <span>Не удалось загрузить товары: {getErrorMessage(feed.error)}</span>
              <Button onClick={feed.retry}>Повторить</Button>
            </div>
          )}
          {!feed.hasMore && feed.loading === null && <span className="ui-muted">Больше товаров нет</span>}
        </div>
      </>
    )
  }

  return (
    <SidebarLayout
      aside={<ProductFiltersPanel value={filters} onChange={setFilters} errors={filterErrors} showSearch={false} />}
    >
      <div className="home-feed__toolbar">
        <h1 className="home-feed__title">
          {filters.q ? (
            <>
              Поиск: «{filters.q}»
              <Button variant="text" onClick={() => setFilters({ ...filters, q: undefined })}>
                Сбросить поиск
              </Button>
            </>
          ) : (
            'Все товары'
          )}
        </h1>
        <label className="home-feed__sort">
          <span className="ui-muted">Сортировка</span>
          <select
            className="ui-input"
            value={sort}
            onChange={(event) => changeSort(parseSort(event.target.value))}
          >
            {PRODUCT_SORTS.map((value) => (
              <option key={value} value={value}>
                {SORT_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="home-feed">
        {refreshing && <LinearProgress />}
        {content}
      </div>
    </SidebarLayout>
  )
}
