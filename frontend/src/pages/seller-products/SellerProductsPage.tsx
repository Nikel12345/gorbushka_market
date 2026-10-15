import { useCallback, useMemo } from 'react'
import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router'
import { ProductTile } from '@/entities/product'
import { getProductFilterErrors, ProductFiltersPanel, useProductFilters } from '@/features/product-filters'
import { useCurrentShop } from '@/features/seller'
import { ApiError, getErrorMessage, sellerApi } from '@/shared/api'
import { formatDate, parsePage, pluralize, updateSearchParams, useRequest } from '@/shared/lib'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LinearProgress,
  LinkButton,
  Loader,
  PageHeader,
  Pagination,
  SidebarLayout,
} from '@/shared/ui'
import type { ProductsOutletContext } from './outletContext'
import './SellerProductsPage.css'

const PRODUCT_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']

/** Товары магазина на продаже: фильтры слева, сетка справа. Карточка и добавление — вложенные маршруты-диалоги. */
export function SellerProductsPage() {
  const shop = useCurrentShop()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const { filters, setFilters, resetFilters, activeCount } = useProductFilters()
  const listPath = `/seller/shops/${shop.id}/products`

  const load = useCallback(
    (signal: AbortSignal) => sellerApi.listProducts(shop.id, { page, ...filters }, { signal }),
    [shop.id, page, filters],
  )
  const products = useRequest(load)
  const { reload } = products
  const resultsOnPage = products.data?.results.length ?? 0

  const outletContext = useMemo<ProductsOutletContext>(
    () => ({
      closeDialog: () => navigate({ pathname: listPath, search: location.search }),
      onProductCreated: () => {
        // Новые товары идут первыми — показываем первую страницу без фильтров
        navigate(listPath)
        reload()
      },
      onProductUpdated: reload,
      onProductArchived: () => {
        // Сняли последний товар на странице — отступаем на страницу назад
        const search =
          resultsOnPage <= 1 && page > 1
            ? `?${updateSearchParams(searchParams, { page: page - 1 })}`
            : location.search
        navigate({ pathname: listPath, search })
        reload()
      },
    }),
    [navigate, listPath, location.search, reload, resultsOnPage, page, searchParams],
  )

  function goToPage(next: number) {
    setSearchParams((prev) => updateSearchParams(prev, { page: next > 1 ? next : null }))
  }

  const refreshing = products.status === 'loading' && Boolean(products.data)
  // 400 на списке — это ошибки значений фильтров: показываем их в панели
  const filterErrors = products.status === 'error' ? getProductFilterErrors(products.error) : undefined

  let content
  if (products.status === 'error') {
    const pageMissing = products.error instanceof ApiError && products.error.status === 404 && page > 1
    content = (
      <Card>
        {pageMissing ? (
          <EmptyState title="Такой страницы нет" action={<Button onClick={() => goToPage(1)}>К первой странице</Button>} />
        ) : filterErrors ? (
          <EmptyState
            title="Проверьте фильтры"
            text="Некоторые значения не подходят — подробности в панели слева."
            action={<Button onClick={resetFilters}>Сбросить фильтры</Button>}
          />
        ) : (
          <ErrorState message={getErrorMessage(products.error)} onRetry={reload} />
        )}
      </Card>
    )
  } else if (!products.data) {
    content = (
      <Card>
        <Loader />
      </Card>
    )
  } else if (products.data.results.length === 0) {
    content = (
      <Card>
        {activeCount > 0 ? (
          <EmptyState
            title="Ничего не найдено"
            text="Попробуйте изменить условия фильтров."
            action={<Button onClick={resetFilters}>Сбросить фильтры</Button>}
          />
        ) : (
          <EmptyState
            title="Пока нет товаров на продаже"
            text="Добавьте первый товар — он сразу появится в каталоге."
            action={
              <LinkButton variant="primary" to="new">
                Добавить товар
              </LinkButton>
            }
          />
        )}
      </Card>
    )
  } else {
    content = (
      <ul className={refreshing ? 'product-grid product-grid--dimmed' : 'product-grid'}>
        {products.data.results.map((product) => {
          const inStock = product.quantity > 0
          return (
            <li key={product.id}>
              <ProductTile
                product={product}
                to={{ pathname: String(product.id), search: location.search }}
                badge={!inStock && 'Нет в наличии'}
                meta={`${inStock ? `${product.quantity} шт.` : 'Нет в наличии'} · ${formatDate(product.created_at)}`}
              />
            </li>
          )
        })}
      </ul>
    )
  }

  let subtitle = shop.name
  if (products.data) {
    subtitle +=
      activeCount > 0
        ? ` · найдено ${pluralize(products.data.count, PRODUCT_WORDS)}`
        : ` · ${pluralize(products.data.count, PRODUCT_WORDS)}`
  }

  return (
    <>
      <PageHeader
        title="Товары на продаже"
        subtitle={subtitle}
        actions={
          <LinkButton variant="primary" to={{ pathname: 'new', search: location.search }}>
            + Добавить товар
          </LinkButton>
        }
      />

      <SidebarLayout
        aside={
          <ProductFiltersPanel value={filters} onChange={setFilters} errors={filterErrors} stockOptions="seller" />
        }
      >
        <div className="products">
          {refreshing && <LinearProgress />}
          {content}
        </div>

        {products.status !== 'error' && products.data && products.data.results.length > 0 && (
          <Pagination
            page={page}
            total={products.data.count}
            hasPrevious={Boolean(products.data.previous)}
            hasNext={Boolean(products.data.next)}
            disabled={products.status === 'loading'}
            onChange={goToPage}
          />
        )}
      </SidebarLayout>

      <Outlet context={outletContext} />
    </>
  )
}
