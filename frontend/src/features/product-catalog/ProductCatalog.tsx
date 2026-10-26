import { useCallback, useState, type ReactNode } from 'react'
import { useLocation, useNavigationType, useSearchParams } from 'react-router'
import { ProductRating, ProductTile } from '@/entities/product'
import { CartControl } from '@/features/cart'
import { getProductFilterErrors, ProductFiltersPanel, useProductFilters } from '@/features/product-filters'
import { catalogApi, getErrorMessage, PRODUCT_SORTS, type ProductSort } from '@/shared/api'
import { updateSearchParams, useCursorFeed, useGridColumns } from '@/shared/lib'
import {
  Button,
  EmptyState,
  ErrorState,
  InfiniteScrollTrigger,
  LinearProgress,
  Loader,
  SidebarLayout,
} from '@/shared/ui'
import { FeedPromo } from './FeedPromo'
import './ProductCatalog.css'

const SORT_LABELS: Record<ProductSort, string> = {
  new: 'Сначала новые',
  price_asc: 'Сначала дешёвые',
  price_desc: 'Сначала дорогие',
}
const DEFAULT_SORT: ProductSort = 'new'

function parseSort(value: string | null): ProductSort {
  return PRODUCT_SORTS.find((sort) => sort === value) ?? DEFAULT_SORT
}

const PROMO_FIRST_ROWS = 3
const PROMO_EVERY_ROWS = 4

/** Строка ленты, после которой идёт реклама: 3, 7, 11, … */
function isPromoRow(row: number): boolean {
  return row >= PROMO_FIRST_ROWS && (row - PROMO_FIRST_ROWS) % PROMO_EVERY_ROWS === 0
}

interface ProductCatalogProps {
  /** Заголовок над лентой, когда нет поиска */
  title: ReactNode
  /** Текст, когда товаров нет совсем (без фильтров) */
  emptyText: string
  /** Рекламные полосы между строками */
  withPromo?: boolean
}

/**
 * Каталог витрины: фильтры слева, сортировка, бесконечная лента. Фильтры и сортировка — в URL
 * (поиск ?q= — из шапки).
 */
export function ProductCatalog({ title, emptyText, withPromo = false }: ProductCatalogProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { filters, setFilters, resetFilters, activeCount } = useProductFilters()
  const sort = parseSort(searchParams.get('sort'))

  const load = useCallback(
    (cursor: string | undefined, signal: AbortSignal) => catalogApi.feed({ ...filters, sort, cursor }, { signal }),
    [filters, sort],
  )
  // «Назад» со страницы товара — показываем уже загруженную ленту, и ScrollRestoration
  // возвращает прокрутку на ту же плитку. Новые фильтры (переход вперёд) — грузим заново, с начала страницы.
  const { pathname, search } = useLocation()
  const navigationType = useNavigationType()
  const feed = useCursorFeed(load, { key: pathname + search, restore: navigationType === 'POP' })

  function changeSort(next: ProductSort) {
    setSearchParams((prev) => updateSearchParams(prev, { sort: next === DEFAULT_SORT ? null : next }))
  }

  const refreshing = feed.loading === 'replace' && !feed.initial

  // Реклама — после строк ленты: первая после PROMO_FIRST_ROWS-й строки, дальше каждые PROMO_EVERY_ROWS.
  // Строки считаем по текущему числу колонок сетки (оно зависит от ширины экрана).
  const [grid, setGrid] = useState<HTMLUListElement | null>(null)
  const columns = useGridColumns(grid)
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
        <EmptyState title="Товаров пока нет" text={emptyText} />
      )
  } else {
    content = (
      <>
        <ul ref={setGrid} className={refreshing ? 'product-grid product-grid--dimmed' : 'product-grid'}>
          {feed.items.map((product, index) => {
            const row = (index + 1) / columns
            const tile = (
              <li key={product.id}>
                <ProductTile
                  product={product}
                  to={`/products/${product.id}`}
                  badge={!product.in_stock && 'Нет в наличии'}
                  meta={<ProductRating value={product.rating} count={product.reviews_count} />}
                  action={<CartControl productId={product.id} variant="compact" canBuy={product.in_stock} />}
                />
              </li>
            )
            // Ключ — номер строки: при смене числа колонок полоса остаётся той же (без нового запроса)
            return withPromo && Number.isInteger(row) && isPromoRow(row)
              ? [tile, <FeedPromo key={`promo-${row}`} />]
              : [tile]
          })}
        </ul>

        <InfiniteScrollTrigger
          onReach={feed.loadMore}
          disabled={!feed.hasMore || feed.loading !== null || feed.failed !== null}
        />
        <div className="catalog__footer">
          {feed.loading === 'more' && <Loader label="Загружаем ещё…" />}
          {feed.failed === 'more' && (
            <div className="catalog__more-error" role="alert">
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
      className="catalog-layout"
      aside={
        // Поиск — в шапке
        <ProductFiltersPanel value={filters} onChange={setFilters} errors={filterErrors} showSearch={false} />
      }
    >
      <div className="catalog__toolbar">
        <h1 className="catalog__title">
          {filters.q ? (
            <>
              Поиск: «{filters.q}»
              <Button variant="text" onClick={() => setFilters({ ...filters, q: undefined })}>
                Сбросить поиск
              </Button>
            </>
          ) : (
            title
          )}
        </h1>
        <label className="catalog__sort">
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

      <div className="catalog">
        {refreshing && <LinearProgress />}
        {content}
      </div>
    </SidebarLayout>
  )
}
