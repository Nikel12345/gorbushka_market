import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { ProductImage } from '@/entities/product'
import { adminApi, getErrorMessage, type Product, type ProductGroup } from '@/shared/api'
import { formatPrice, useRequest } from '@/shared/lib'
import { Chip, EmptyState, ErrorState, Loader, Pagination } from '@/shared/ui'
import './catalogAdmin.css'

interface GroupProductsProps {
  group: ProductGroup
  /** Открытый сейчас товар: его строка подсвечена и не ссылка */
  currentId?: number
  /** Колонка «Создать вариант» — новый товар с копией полей этого */
  withCopy?: boolean
}

/** Товары группы таблицей: колонка на каждую ось — сразу видно, каких сочетаний не хватает. */
export function GroupProducts({ group, currentId, withCopy = false }: GroupProductsProps) {
  const [page, setPage] = useState(1)
  const load = useCallback(
    (signal: AbortSignal) => adminApi.listProducts({ group: group.id, page }, { signal }),
    [group.id, page],
  )
  const products = useRequest(load)

  if (products.status === 'error') {
    return <ErrorState message={getErrorMessage(products.error)} onRetry={products.reload} />
  }
  if (!products.data) return <Loader />
  if (products.data.results.length === 0) {
    return <EmptyState title="В группе пока нет товаров" text="Добавьте товар и выберите эту группу в его карточке." />
  }

  return (
    <>
      <div className="ui-table-wrap">
        <table className="ui-table group-products">
          <thead>
            <tr>
              <th>Товар</th>
              {group.axes.map((axis) => (
                <th key={axis.id}>{axis.name}</th>
              ))}
              <th className="ui-table__num">Цена</th>
              <th className="ui-table__num">Остаток</th>
              {withCopy && <th aria-label="Действия" />}
            </tr>
          </thead>
          <tbody>
            {products.data.results.map((product) => (
              <GroupProductRow
                key={product.id}
                product={product}
                group={group}
                current={product.id === currentId}
                withCopy={withCopy}
              />
            ))}
          </tbody>
        </table>
      </div>
      {(products.data.previous || products.data.next) && (
        <Pagination
          page={page}
          total={products.data.count}
          hasPrevious={Boolean(products.data.previous)}
          hasNext={Boolean(products.data.next)}
          disabled={products.status === 'loading'}
          onChange={setPage}
        />
      )}
    </>
  )
}

function GroupProductRow({
  product,
  group,
  current,
  withCopy,
}: {
  product: Product
  group: ProductGroup
  current: boolean
  withCopy: boolean
}) {
  return (
    <tr className={current ? 'ui-table__row--active' : undefined}>
      <td>
        <div className="group-products__title">
          <ProductImage src={product.image} alt="" className="group-products__image" />
          {current ? (
            <span>
              {product.title} <Chip>этот товар</Chip>
            </span>
          ) : (
            <Link to={`/seller/products/${product.id}`}>{product.title}</Link>
          )}
        </div>
      </td>
      {group.axes.map((axis) => {
        const value = product.characteristics.find((item) => item.characteristic_id === axis.id)
        return <td key={axis.id}>{value ? value.value : <span className="ui-muted">—</span>}</td>
      })}
      <td className="ui-table__num">{formatPrice(product.price)}</td>
      <td className="ui-table__num">
        {product.quantity > 0 ? `${product.quantity} шт.` : <Chip tone="warning">нет</Chip>}
      </td>
      {withCopy && (
        <td className="ui-table__num">
          <Link
            to={`/seller/products/new?from=${product.id}`}
            className="group-products__copy"
            title="Новый товар с полями этого — останется поменять характеристики и фото"
          >
            + Вариант
          </Link>
        </td>
      )}
    </tr>
  )
}
