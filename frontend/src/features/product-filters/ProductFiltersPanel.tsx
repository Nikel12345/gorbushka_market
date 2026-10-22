import { useId, useState, type FormEvent } from 'react'
import type { Category, FieldErrors, ProductFilterParams } from '@/shared/api'
import { Button, FieldError } from '@/shared/ui'
import { countActiveFilters, normalizePrice } from './model'
import './ProductFiltersPanel.css'

type StockValue = 'all' | 'in' | 'out'

const STOCK_OPTIONS: Record<'buyer' | 'seller', { value: StockValue; label: string }[]> = {
  buyer: [
    { value: 'all', label: 'Все товары' },
    { value: 'in', label: 'Только в наличии' },
  ],
  seller: [
    { value: 'all', label: 'Все' },
    { value: 'in', label: 'В наличии' },
    { value: 'out', label: 'Нет в наличии' },
  ],
}

const toStock = (value?: boolean): StockValue => (value === undefined ? 'all' : value ? 'in' : 'out')
const fromStock = (value: StockValue): boolean | undefined => (value === 'all' ? undefined : value === 'in')

interface Draft {
  q: string
  price_min: string
  price_max: string
}

const toDraft = (value: ProductFilterParams): Draft => ({
  q: value.q ?? '',
  price_min: value.price_min ?? '',
  price_max: value.price_max ?? '',
})

interface ProductFiltersPanelProps {
  value: ProductFilterParams
  onChange: (next: ProductFilterParams) => void
  /** Ошибки валидации фильтров от API (400) */
  errors?: FieldErrors
  /** Показывать ли поиск (на главной он может жить в шапке) */
  showSearch?: boolean
  /** Продавцу нужен вариант «Нет в наличии», покупателю — нет */
  stockOptions?: 'buyer' | 'seller'
  /** Дерево категорий для выбора (плоский список, как отдаёт API); нет — без выбора категории */
  categories?: Category[]
}

/**
 * Панель фильтров товаров. Только форма: не знает ни про API, ни про страницу.
 * Где стоит и как грузятся товары — решает страница (см. useProductFilters).
 * Текстовые поля применяются кнопкой/Enter, наличие и категория — сразу.
 */
export function ProductFiltersPanel({
  value,
  onChange,
  errors,
  showSearch = true,
  stockOptions = 'buyer',
  categories,
}: ProductFiltersPanelProps) {
  const id = useId()
  const [draft, setDraft] = useState(() => toDraft(value))
  const [localErrors, setLocalErrors] = useState<FieldErrors>({})
  const [open, setOpen] = useState(false)

  // Фильтры сменились снаружи (применили, «назад» в браузере) — подтягиваем поля
  const [syncedValue, setSyncedValue] = useState(value)
  if (value !== syncedValue) {
    setSyncedValue(value)
    setDraft(toDraft(value))
    setLocalErrors({})
  }

  const activeCount = countActiveFilters(value)
  const allErrors = { ...errors, ...localErrors }
  const priceErrors = [...(allErrors.price_min ?? []), ...(allErrors.price_max ?? [])]

  /** Применить поля ввода вместе с тем, что выбрано сразу (наличие, категория) */
  function apply(changes: Pick<ProductFilterParams, 'in_stock' | 'category'> = {}) {
    const instant = { in_stock: value.in_stock, category: value.category, ...changes }
    const priceMin = normalizePrice(draft.price_min)
    const priceMax = normalizePrice(draft.price_max)

    if (priceMin === null || priceMax === null) {
      setLocalErrors({ price_min: ['Цена — число, например 1500 или 1499,90.'] })
      return
    }
    if (priceMin && priceMax && Number(priceMin) > Number(priceMax)) {
      setLocalErrors({ price_min: ['Цена «от» больше цены «до».'] })
      return
    }

    setLocalErrors({})
    onChange({
      q: draft.q.trim() || undefined,
      price_min: priceMin || undefined,
      price_max: priceMax || undefined,
      in_stock: instant.in_stock,
      category: instant.category,
    })
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    apply()
  }

  function handleReset() {
    setDraft(toDraft({}))
    setLocalErrors({})
    onChange({})
  }

  const update = (field: keyof Draft) => (event: { target: { value: string } }) =>
    setDraft((prev) => ({ ...prev, [field]: event.target.value }))

  const draftEmpty = !draft.q && !draft.price_min && !draft.price_max

  return (
    <aside className={open ? 'product-filters product-filters--open' : 'product-filters'} aria-label="Фильтры товаров">
      <div className="product-filters__header">
        <h2 className="product-filters__title">Фильтры</h2>
        {activeCount > 0 && <span className="product-filters__count">{activeCount}</span>}
        <button
          type="button"
          className="product-filters__toggle"
          aria-expanded={open}
          aria-controls={`${id}-body`}
          onClick={() => setOpen((prev) => !prev)}
        >
          {open ? 'Скрыть' : 'Показать'}
        </button>
      </div>

      <form id={`${id}-body`} className="product-filters__body" onSubmit={handleSubmit} noValidate>
        {showSearch && (
          <div className="product-filters__group">
            <label className="product-filters__label" htmlFor={`${id}-q`}>
              Поиск
            </label>
            <input
              id={`${id}-q`}
              className="ui-input"
              type="search"
              placeholder="Название или описание"
              value={draft.q}
              onChange={update('q')}
              aria-invalid={Boolean(allErrors.q)}
            />
            <FieldError messages={allErrors.q} />
          </div>
        )}

        {categories && (
          <div className="product-filters__group">
            <label className="product-filters__label" htmlFor={`${id}-category`}>
              Категория
            </label>
            <select
              id={`${id}-category`}
              className="ui-input"
              value={value.category ?? ''}
              onChange={(event) => apply({ category: event.target.value ? Number(event.target.value) : undefined })}
              aria-invalid={Boolean(allErrors.category)}
            >
              <option value="">Все категории</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {`${'\u00a0'.repeat(4 * category.depth)}${category.name}`}
                </option>
              ))}
            </select>
            <FieldError messages={allErrors.category} />
          </div>
        )}

        <fieldset className="product-filters__group">
          <legend className="product-filters__label">Цена, ₽</legend>
          <div className="product-filters__range">
            <input
              className="ui-input"
              inputMode="decimal"
              placeholder="от"
              aria-label="Цена от"
              value={draft.price_min}
              onChange={update('price_min')}
              aria-invalid={Boolean(allErrors.price_min)}
            />
            <span aria-hidden="true">—</span>
            <input
              className="ui-input"
              inputMode="decimal"
              placeholder="до"
              aria-label="Цена до"
              value={draft.price_max}
              onChange={update('price_max')}
              aria-invalid={Boolean(allErrors.price_max)}
            />
          </div>
          <FieldError messages={priceErrors} />
        </fieldset>

        <fieldset className="product-filters__group">
          <legend className="product-filters__label">Наличие</legend>
          {STOCK_OPTIONS[stockOptions].map((option) => (
            <label key={option.value} className="product-filters__option">
              <input
                type="radio"
                name={`${id}-stock`}
                checked={toStock(value.in_stock) === option.value}
                onChange={() => apply({ in_stock: fromStock(option.value) })}
              />
              {option.label}
            </label>
          ))}
          <FieldError messages={allErrors.in_stock} />
        </fieldset>

        <div className="product-filters__actions">
          <Button type="submit" variant="primary">
            Применить
          </Button>
          <Button variant="text" onClick={handleReset} disabled={activeCount === 0 && draftEmpty}>
            Сбросить
          </Button>
        </div>
      </form>
    </aside>
  )
}
