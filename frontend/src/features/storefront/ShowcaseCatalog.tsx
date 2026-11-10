import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useLocation, useNavigationType, useSearchParams } from 'react-router'
import type { ShowcaseDesignId } from '@/features/design-switcher'
import { normalizePrice, useProductFilters } from '@/features/product-filters'
import { catalogApi, getErrorMessage, PRODUCT_SORTS, type ProductFilterParams, type ProductSort } from '@/shared/api'
import { updateSearchParams, useCursorFeed } from '@/shared/lib'
import { Button, EmptyState, ErrorState, Loader } from '@/shared/ui'
import { useCategories } from './hooks'
import { CheckIcon, ChevronIcon, SlidersIcon } from './icons'
import { ShowcaseTile } from './ShowcaseTile'

const SORT_LABELS: Record<ProductSort, string> = {
  new: 'Сначала новые',
  price_asc: 'Сначала дешёвые',
  price_desc: 'Сначала дорогие',
}

function parseSort(value: string | null): ProductSort {
  return PRODUCT_SORTS.find((sort) => sort === value) ?? 'new'
}

/** Бренды для фильтра: отдельного поля в каталоге нет — ищем по названию (?q=) */
const BRANDS = ['Apple', 'Samsung', 'Sony', 'Xiaomi', 'DJI', 'JBL', 'Яндекс']

// --- Выпадающее окно у чипса ---

function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) close()
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])
  return ref
}

function ChipMenu({
  label,
  active,
  icon,
  chevron = true,
  children,
}: {
  label: ReactNode
  active?: boolean
  icon?: ReactNode
  chevron?: boolean
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const ref = useDismiss(open, close)

  return (
    <div className="sc-chipmenu" ref={ref}>
      <button
        type="button"
        className={['sc-filter-chip', active && 'sc-filter-chip--active', open && 'sc-filter-chip--open'].filter(Boolean).join(' ')}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {icon}
        {label}
        {chevron && <ChevronIcon />}
      </button>
      {open && <div className="sc-chipmenu__panel">{children(close)}</div>}
    </div>
  )
}

/** Цена от/до: применяется по кнопке; неверное значение — подсказка под полями */
function PriceForm({
  filters,
  onApply,
  submitLabel = 'Применить',
}: {
  filters: ProductFilterParams
  onApply: (range: { price_min?: string; price_max?: string }) => void
  submitLabel?: string
}) {
  const [min, setMin] = useState(filters.price_min ?? '')
  const [max, setMax] = useState(filters.price_max ?? '')
  const [error, setError] = useState(false)

  function submit(event: FormEvent) {
    event.preventDefault()
    const priceMin = normalizePrice(min)
    const priceMax = normalizePrice(max)
    if (priceMin === null || priceMax === null) {
      setError(true)
      return
    }
    setError(false)
    onApply({ price_min: priceMin || undefined, price_max: priceMax || undefined })
  }

  return (
    <form className="sc-price" onSubmit={submit} noValidate>
      <div className="sc-price__range">
        <label>
          <span className="ui-sr-only">Цена от</span>
          <input inputMode="decimal" placeholder="от" value={min} onChange={(event) => setMin(event.target.value)} />
        </label>
        <span aria-hidden="true">—</span>
        <label>
          <span className="ui-sr-only">Цена до</span>
          <input inputMode="decimal" placeholder="до" value={max} onChange={(event) => setMax(event.target.value)} />
        </label>
      </div>
      {error && <p className="sc-price__error">Введите цену числом, например 15000</p>}
      <button type="submit" className="sc-apply">
        {submitLabel}
      </button>
    </form>
  )
}

/** Чипсы над лентой («Витрина», «Афиша») */
function FilterChips() {
  const { filters, setFilters, resetFilters, activeCount } = useProductFilters()
  const categories = useCategories()
  const brand = BRANDS.find((item) => item.toLowerCase() === filters.q?.toLowerCase())
  const category = categories.find((item) => item.id === filters.category)
  const hasPrice = Boolean(filters.price_min || filters.price_max)

  return (
    <div className="sc-filter-chips">
      <ChipMenu label="Все фильтры" icon={<SlidersIcon />} chevron={false} active={activeCount > 0}>
        {(close) => (
          <div className="sc-filters-panel">
            <span className="sc-filters-panel__label">Цена, ₽</span>
            <PriceForm
              filters={filters}
              submitLabel="Показать"
              onApply={(range) => {
                setFilters({ ...filters, ...range })
                close()
              }}
            />
            <label className="sc-check">
              <input
                type="checkbox"
                checked={filters.in_stock === true}
                onChange={(event) => setFilters({ ...filters, in_stock: event.target.checked ? true : undefined })}
              />
              Только в наличии
            </label>
            {activeCount > 0 && (
              <button
                type="button"
                className="sc-reset"
                onClick={() => {
                  resetFilters()
                  close()
                }}
              >
                Сбросить все фильтры
              </button>
            )}
          </div>
        )}
      </ChipMenu>

      <button
        type="button"
        className={filters.in_stock ? 'sc-filter-chip sc-filter-chip--active' : 'sc-filter-chip'}
        aria-pressed={filters.in_stock === true}
        onClick={() => setFilters({ ...filters, in_stock: filters.in_stock ? undefined : true })}
      >
        {filters.in_stock && <CheckIcon />}В наличии
      </button>

      <ChipMenu label="Цена" active={hasPrice}>
        {(close) => (
          <PriceForm
            filters={filters}
            onApply={(range) => {
              setFilters({ ...filters, ...range })
              close()
            }}
          />
        )}
      </ChipMenu>

      <ChipMenu label={brand ? `Бренд: ${brand}` : 'Бренд'} active={Boolean(brand)}>
        {(close) => (
          <ul className="sc-options">
            {BRANDS.map((item) => (
              <li key={item}>
                <button
                  type="button"
                  className={item === brand ? 'sc-option sc-option--active' : 'sc-option'}
                  onClick={() => {
                    setFilters({ ...filters, q: item === brand ? undefined : item })
                    close()
                  }}
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        )}
      </ChipMenu>

      <ChipMenu label={category ? category.name : 'Категория'} active={Boolean(category)}>
        {(close) => (
          <ul className="sc-options sc-options--scroll">
            <li>
              <button
                type="button"
                className={!category ? 'sc-option sc-option--active' : 'sc-option'}
                onClick={() => {
                  setFilters({ ...filters, category: undefined })
                  close()
                }}
              >
                Все категории
              </button>
            </li>
            {categories.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={item.id === category?.id ? 'sc-option sc-option--active' : 'sc-option'}
                  style={{ paddingLeft: 14 + item.depth * 14 }}
                  onClick={() => {
                    setFilters({ ...filters, category: item.id })
                    close()
                  }}
                >
                  {item.name}
                  <span className="sc-option__count">{item.products_count}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </ChipMenu>
    </div>
  )
}

const NIGHT_CATEGORIES_SHOWN = 6

/** Панель фильтров слева («Ночь») */
function NightFilters({ open }: { open: boolean }) {
  const { filters, setFilters, resetFilters } = useProductFilters()
  const categories = useCategories()
  const [allCategories, setAllCategories] = useState(false)
  const brand = BRANDS.find((item) => item.toLowerCase() === filters.q?.toLowerCase())

  // Сначала самые наполненные подкатегории; выбранная — всегда в списке
  const leaves = categories.filter((item) => item.depth > 0).sort((a, b) => b.products_count - a.products_count)
  const shown = allCategories ? leaves : leaves.slice(0, NIGHT_CATEGORIES_SHOWN)
  const selected = leaves.find((item) => item.id === filters.category)
  if (selected && !shown.includes(selected)) shown.push(selected)

  return (
    <aside className={open ? 'sc-night-filters sc-night-filters--open' : 'sc-night-filters'} aria-label="Фильтры">
      <h3 className="sc-night-filters__title">Фильтры</h3>

      <fieldset className="sc-night-filters__group">
        <legend>Категория</legend>
        {shown.map((item) => (
          <label key={item.id} className="sc-check">
            <input
              type="checkbox"
              checked={filters.category === item.id}
              onChange={(event) => setFilters({ ...filters, category: event.target.checked ? item.id : undefined })}
            />
            {item.name}
            <span className="sc-check__count">{item.products_count}</span>
          </label>
        ))}
        {leaves.length > NIGHT_CATEGORIES_SHOWN && (
          <button type="button" className="sc-text-button" onClick={() => setAllCategories((value) => !value)}>
            {allCategories ? 'Свернуть' : 'Все категории'}
          </button>
        )}
      </fieldset>

      <fieldset className="sc-night-filters__group">
        <legend>Цена, ₽</legend>
        <PriceForm
          key={`${filters.price_min ?? ''}-${filters.price_max ?? ''}`}
          filters={filters}
          submitLabel="Показать"
          onApply={(range) => setFilters({ ...filters, ...range })}
        />
      </fieldset>

      <fieldset className="sc-night-filters__group">
        <legend>Бренд</legend>
        <div className="sc-pills">
          {BRANDS.slice(0, 5).map((item) => (
            <button
              key={item}
              type="button"
              className={item === brand ? 'sc-pill sc-pill--active' : 'sc-pill'}
              aria-pressed={item === brand}
              onClick={() => setFilters({ ...filters, q: item === brand ? undefined : item })}
            >
              {item}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="sc-night-filters__group">
        <label className="sc-check">
          <input
            type="checkbox"
            checked={filters.in_stock === true}
            onChange={(event) => setFilters({ ...filters, in_stock: event.target.checked ? true : undefined })}
          />
          Только в наличии
        </label>
      </div>

      <button type="button" className="sc-reset" onClick={resetFilters}>
        Сбросить
      </button>
    </aside>
  )
}

/**
 * Лента главной «витринных» вариантов (как в макетах): заголовок и сортировка, фильтры чипсами
 * («Витрина», «Афиша») или панелью слева («Ночь»), сетка плиток, «Показать ещё».
 * Фильтры и сортировка — в URL, как у обычного каталога.
 */
export function ShowcaseCatalog({
  design,
  title,
  heading = 'h2',
}: {
  design: ShowcaseDesignId
  title: ReactNode
  /** h1 — когда над лентой нет первого экрана (поиск, категория) */
  heading?: 'h1' | 'h2'
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { filters, resetFilters, activeCount } = useProductFilters()
  const sort = parseSort(searchParams.get('sort'))
  const [filtersOpen, setFiltersOpen] = useState(false)

  const load = useCallback(
    (cursor: string | undefined, signal: AbortSignal) => catalogApi.feed({ ...filters, sort, cursor }, { signal }),
    [filters, sort],
  )
  const { pathname, search } = useLocation()
  const navigationType = useNavigationType()
  const feed = useCursorFeed(load, { key: pathname + search, restore: navigationType === 'POP' })

  function changeSort(next: ProductSort) {
    setSearchParams((prev) => updateSearchParams(prev, { sort: next === 'new' ? null : next }))
  }

  const Heading = heading
  const refreshing = feed.loading === 'replace' && !feed.initial

  let content: ReactNode
  if (feed.failed === 'replace') {
    content = <ErrorState message={getErrorMessage(feed.error)} onRetry={feed.retry} />
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
        <EmptyState title="Товаров пока нет" text="Загляните позже — скоро здесь появятся товары." />
      )
  } else {
    content = (
      <>
        <ul className={refreshing ? 'sc-grid sc-grid--dimmed' : 'sc-grid'}>
          {feed.items.map((product) => (
            <li key={product.id}>
              <ShowcaseTile product={product} />
            </li>
          ))}
        </ul>
        <div className="sc-more-row">
          {feed.failed === 'more' ? (
            <div className="sc-more-error" role="alert">
              Не удалось загрузить товары: {getErrorMessage(feed.error)}
              <Button onClick={feed.retry}>Повторить</Button>
            </div>
          ) : (
            feed.hasMore && (
              <button type="button" className="sc-more" onClick={feed.loadMore} disabled={feed.loading !== null}>
                {feed.loading === 'more' ? 'Загружаем…' : 'Показать ещё'}
              </button>
            )
          )}
        </div>
      </>
    )
  }

  return (
    <section className={`sc-catalog-section sc-catalog-section--${design}`}>
      <div className="sc-catalog-head">
        <div className="sc-catalog-head__text">
          <Heading className="sc-catalog-head__title">{title}</Heading>
          {design === 'night' && <p className="sc-catalog-head__sub">Товары павильонов ТЦ на Барклая, 8</p>}
        </div>
        <div className="sc-catalog-head__tools">
          {design === 'night' && (
            <button
              type="button"
              className="sc-filters-toggle"
              aria-expanded={filtersOpen}
              onClick={() => setFiltersOpen((value) => !value)}
            >
              <SlidersIcon />
              Фильтры{activeCount > 0 ? ` · ${activeCount}` : ''}
            </button>
          )}
          <label className="sc-sort">
            <span className="sc-sort__label">Сортировка</span>
            <select value={sort} onChange={(event) => changeSort(parseSort(event.target.value))}>
              {PRODUCT_SORTS.map((value) => (
                <option key={value} value={value}>
                  {SORT_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {design !== 'night' && <FilterChips />}

      <div className={design === 'night' ? 'sc-catalog-body sc-catalog-body--aside' : 'sc-catalog-body'}>
        {design === 'night' && <NightFilters open={filtersOpen} />}
        <div className="sc-catalog-main">{content}</div>
      </div>
    </section>
  )
}
