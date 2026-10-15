import { useCallback, useMemo } from 'react'
import { Link, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router'
import { useCurrentShop } from '@/features/seller'
import { ApiError, getErrorMessage, sellerApi, type Product } from '@/shared/api'
import { formatDate, formatPrice, parsePage, pluralize, updateSearchParams, useRequest } from '@/shared/lib'
import {
  Card,
  Chip,
  EmptyState,
  ErrorState,
  LinearProgress,
  LinkButton,
  Loader,
  PageHeader,
  Pagination,
} from '@/shared/ui'
import type { ProductsOutletContext } from './outletContext'
import './SellerProductsPage.css'

/** Товары магазина на продаже. Карточка и добавление — вложенные маршруты-диалоги. */
export function SellerProductsPage() {
  const shop = useCurrentShop()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const listPath = `/seller/shops/${shop.id}/products`

  const load = useCallback(
    (signal: AbortSignal) => sellerApi.listProducts(shop.id, { page }, { signal }),
    [shop.id, page],
  )
  const products = useRequest(load)
  const { reload } = products
  const resultsOnPage = products.data?.results.length ?? 0

  const outletContext = useMemo<ProductsOutletContext>(
    () => ({
      closeDialog: () => navigate({ pathname: listPath, search: location.search }),
      onProductCreated: () => {
        // Новые товары идут первыми — показываем первую страницу
        navigate(listPath)
        reload()
      },
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

  function openProduct(product: Product) {
    navigate({ pathname: `${listPath}/${product.id}`, search: location.search })
  }

  let content
  if (products.status === 'error') {
    const pageMissing = products.error instanceof ApiError && products.error.status === 404 && page > 1
    content = pageMissing ? (
      <EmptyState
        title="Такой страницы нет"
        action={<LinkButton to={listPath}>К первой странице</LinkButton>}
      />
    ) : (
      <ErrorState message={getErrorMessage(products.error)} onRetry={reload} />
    )
  } else if (!products.data) {
    content = <Loader />
  } else if (products.data.results.length === 0) {
    content = (
      <EmptyState
        title="Пока нет товаров на продаже"
        text="Добавьте первый товар — он сразу появится в каталоге."
        action={
          <LinkButton variant="primary" to="new">
            Добавить товар
          </LinkButton>
        }
      />
    )
  } else {
    content = (
      <div className="ui-table-wrap">
        <table className="ui-table">
          <thead>
            <tr>
              <th>Название</th>
              <th className="ui-table__num">Цена</th>
              <th className="ui-table__num">В наличии</th>
              <th>Добавлен</th>
            </tr>
          </thead>
          <tbody>
            {products.data.results.map((product) => (
              <tr
                key={product.id}
                className="ui-table__row--clickable"
                onClick={(event) => {
                  // Клик по самой ссылке обработает Link
                  if (!(event.target as HTMLElement).closest('a')) openProduct(product)
                }}
              >
                <td>
                  <Link
                    className="products__title"
                    to={{ pathname: String(product.id), search: location.search }}
                  >
                    {product.title}
                  </Link>
                  {product.description && <div className="products__description">{product.description}</div>}
                </td>
                <td className="ui-table__num">{formatPrice(product.price)}</td>
                <td className="ui-table__num">
                  {product.quantity > 0 ? `${product.quantity} шт.` : <Chip tone="warning">Нет в наличии</Chip>}
                </td>
                <td className="products__date">{formatDate(product.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title="Товары на продаже"
        subtitle={
          products.data ? `${shop.name} · ${pluralize(products.data.count, ['товар', 'товара', 'товаров'])}` : shop.name
        }
        actions={
          <LinkButton variant="primary" to={{ pathname: 'new', search: location.search }}>
            Добавить товар
          </LinkButton>
        }
      />

      <Card flush>
        {products.status === 'loading' && products.data && <LinearProgress />}
        {content}
      </Card>

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

      <Outlet context={outletContext} />
    </>
  )
}
