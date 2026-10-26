import { useCallback, useId, useState } from 'react'
import { Link } from 'react-router'
import { ProductImage } from '@/entities/product'
import { CategorySelect, categoryPathLabel, type CategoriesRequest } from '@/features/seller'
import {
  adminApi,
  getErrorMessage,
  getFieldErrors,
  PRODUCT_ACCESSORIES_MAX,
  type AccessoryCard,
  type Product,
} from '@/shared/api'
import { formatPrice, useDebouncedValue, useRequest } from '@/shared/lib'
import { Button, Card, Chip, EmptyState, ErrorState, Field, FieldError, Loader } from '@/shared/ui'
import { ProductSelect } from './ProductSelect'
import './ProductAccessories.css'

interface ProductAccessoriesProps {
  /** Сохранённый товар: его группа решает, чей это список */
  product: Product
  /** Дерево категорий для фильтра — то же, что у формы товара */
  categories: CategoriesRequest
}

/**
 * Аксессуары товара — раздел «Аксессуары» на витрине, в этом порядке. У товара группы вариантов
 * список общий для всей группы. Каждое изменение сразу уходит на сервер, без кнопки «Сохранить».
 */
export function ProductAccessories({ product, categories }: ProductAccessoriesProps) {
  const load = useCallback(
    (signal: AbortSignal) => adminApi.listProductAccessories(product.id, { signal }),
    [product.id],
  )
  const accessories = useRequest(load)
  const { mutate, reload } = accessories
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<string[]>()

  const items = accessories.data ?? []
  const ids = items.map((item) => item.id)

  async function save(next: number[]) {
    setSaving(true)
    setErrors(undefined)
    try {
      const saved = await adminApi.setProductAccessories(product.id, next)
      mutate(() => saved)
    } catch (error) {
      setErrors(Object.values(getFieldErrors(error)).flat())
      // Список мог измениться в другой вкладке — показываем, что на самом деле сохранено
      reload()
    } finally {
      setSaving(false)
    }
  }

  function move(index: number, shift: -1 | 1) {
    const next = [...ids]
    ;[next[index], next[index + shift]] = [next[index + shift], next[index]]
    void save(next)
  }

  const where = product.group
    ? `Общие для всех товаров группы «${product.group.name}»: изменения видны у всех вариантов.`
    : 'Показываются на странице товара в этом порядке.'

  let list
  if (!accessories.data) {
    list =
      accessories.status === 'error' ? (
        <ErrorState message={getErrorMessage(accessories.error)} onRetry={reload} />
      ) : (
        <Loader />
      )
  } else if (items.length === 0) {
    list = <EmptyState title="Аксессуаров пока нет" text="Выберите товар выше — он появится на витрине под карточкой." />
  } else {
    list = (
      <div className="ui-table-wrap">
        <table className="ui-table accessories">
          <thead>
            <tr>
              <th>Товар</th>
              <th>Категория</th>
              <th className="ui-table__num">Цена</th>
              <th className="ui-table__num">Наличие</th>
              <th aria-label="Действия" />
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <AccessoryRow
                key={item.id}
                item={item}
                categories={categories}
                disabled={saving}
                isFirst={index === 0}
                isLast={index === items.length - 1}
                onUp={() => move(index, -1)}
                onDown={() => move(index, 1)}
                onRemove={() => void save(ids.filter((id) => id !== item.id))}
              />
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <Card
      title="Аксессуары"
      actions={
        <span className="product-editor__count">
          {items.length} из {PRODUCT_ACCESSORIES_MAX}
        </span>
      }
    >
      <div className="accessories-field">
        <p className="product-editor__hint">{where} Изменения сохраняются сразу.</p>
        <AccessoryPicker
          product={product}
          categories={categories}
          taken={new Set(ids)}
          full={items.length >= PRODUCT_ACCESSORIES_MAX}
          disabled={saving || !accessories.data}
          onAdd={(id) => void save([...ids, id])}
        />
        <FieldError messages={errors} />
        {list}
      </div>
    </Card>
  )
}

interface AccessoryRowProps {
  item: AccessoryCard
  categories: CategoriesRequest
  disabled: boolean
  isFirst: boolean
  isLast: boolean
  onUp: () => void
  onDown: () => void
  onRemove: () => void
}

function AccessoryRow({ item, categories, disabled, isFirst, isLast, onUp, onDown, onRemove }: AccessoryRowProps) {
  // Колонка узкая: только название, путь от верхнего уровня — во всплывающей подсказке
  let category = <span className="ui-muted">—</span>
  if (item.category) {
    const path = categories.data ? categoryPathLabel(categories.data, item.category) : item.category.name
    category = <span title={path}>{item.category.name}</span>
  }

  return (
    <tr>
      <td>
        <div className="accessories__title">
          <ProductImage src={item.image} alt="" className="accessories__image" />
          <Link to={`/seller/products/${item.id}`}>{item.title}</Link>
        </div>
      </td>
      <td>{category}</td>
      <td className="ui-table__num">{formatPrice(item.price)}</td>
      <td className="ui-table__num">{item.in_stock ? 'есть' : <Chip tone="warning">нет</Chip>}</td>
      <td className="ui-table__num">
        <div className="accessories__actions">
          <Button variant="text" onClick={onUp} disabled={disabled || isFirst} title="Выше" aria-label="Выше">
            ↑
          </Button>
          <Button variant="text" onClick={onDown} disabled={disabled || isLast} title="Ниже" aria-label="Ниже">
            ↓
          </Button>
          <Button variant="text" onClick={onRemove} disabled={disabled}>
            Убрать
          </Button>
        </div>
      </td>
    </tr>
  )
}

interface AccessoryPickerProps {
  product: Product
  categories: CategoriesRequest
  /** Уже в списке — в выпадающем списке недоступны */
  taken: Set<number>
  full: boolean
  disabled: boolean
  onAdd: (productId: number) => void
}

/**
 * Добавить аксессуар: фильтры по категории (всё дерево, с подкатегориями) и названию,
 * затем товар из выпадающего списка найденных — с фото, ценой и наличием.
 */
function AccessoryPicker({ product, categories, taken, full, disabled, onAdd }: AccessoryPickerProps) {
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const q = useDebouncedValue(query.trim())
  const productLabelId = useId()

  const load = useCallback(
    (signal: AbortSignal) =>
      adminApi.listProducts({ q: q || undefined, category: categoryId ?? undefined }, { signal }),
    [q, categoryId],
  )
  const found = useRequest(load)

  /** Почему товар нельзя выбрать; undefined — можно */
  function unavailable(item: Product): string | undefined {
    if (item.id === product.id) return 'этот товар'
    if (product.group && item.group?.id === product.group.id) return 'вариант этого товара'
    if (taken.has(item.id)) return 'уже в списке'
  }

  const options = found.data?.results ?? []
  const selected = options.find((item) => item.id === selectedId && !unavailable(item))

  let placeholder = `Выберите товар (${options.length})`
  if (!found.data) placeholder = found.status === 'error' ? 'Товары не загрузились' : 'Ищем товары…'
  else if (options.length === 0) placeholder = 'Ничего не нашлось — измените фильтр'

  let hint
  if (full) hint = `Больше ${PRODUCT_ACCESSORIES_MAX} аксессуаров добавить нельзя — сначала уберите лишние.`
  else if (found.data && found.data.count > options.length) {
    hint = `Показаны первые ${options.length} из ${found.data.count} — уточните категорию или название.`
  }

  return (
    <div className="accessory-picker">
      <div className="accessory-picker__filters">
        <Field label="Категория">
          <CategorySelect
            categories={categories}
            value={categoryId}
            onChange={setCategoryId}
            emptyLabel="Все категории"
          />
        </Field>
        <Field label="Название">
          <input
            className="ui-input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Например, чехол"
          />
        </Field>
      </div>
      <div className="accessory-picker__choose">
        {/* Не Field: клик по пустому месту списка внутри <label> снова нажимал бы кнопку */}
        <div className="ui-field">
          <span id={productLabelId} className="ui-field__label">
            Товар
          </span>
          <ProductSelect
            options={options}
            value={selected}
            onChange={(item) => setSelectedId(item.id)}
            unavailable={unavailable}
            placeholder={placeholder}
            labelId={productLabelId}
            loading={found.status === 'loading'}
            disabled={options.length === 0}
          />
        </div>
        {found.status === 'error' && <Button onClick={found.reload}>Повторить</Button>}
        <Button
          variant="primary"
          disabled={!selected || full || disabled}
          onClick={() => {
            if (!selected) return
            onAdd(selected.id)
            setSelectedId(null)
          }}
        >
          Добавить
        </Button>
      </div>
      {hint && <span className="ui-field__hint">{hint}</span>}
    </div>
  )
}
